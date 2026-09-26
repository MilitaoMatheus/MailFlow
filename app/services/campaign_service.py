import os
import time
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.campaign import Campaign, CampaignStatus, CampaignContactStatus
from app.models.contact import ContactStatus
from app.models.user import User
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.template_repository import TemplateRepository
from app.repositories.log_repository import LogRepository
from app.services.template_service import TemplateService
from app.services.email_service import EmailService
from app.services.security_service import SecurityService
from app.config import settings


class CampaignService:
    """Serviço de gerenciamento, montagem e execução resiliente de campanhas de e-mail."""

    def __init__(self, db: Session):
        self.db = db
        self.campaign_repo = CampaignRepository(db)
        self.contact_repo = ContactRepository(db)
        self.template_repo = TemplateRepository(db)
        self.log_repo = LogRepository(db)
        self.email_service = EmailService(db)
        self.template_service = TemplateService(db)

    def list_campaigns(self, user_id: int, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        offset = (max(1, page) - 1) * page_size
        campaigns = self.campaign_repo.list_campaigns(user_id, limit=page_size, offset=offset)
        total_count = self.campaign_repo.count_campaigns(user_id)
        total_pages = max(1, (total_count + page_size - 1) // page_size)

        return {
            "campaigns": campaigns,
            "total_count": total_count,
            "current_page": page,
            "total_pages": total_pages
        }

    def get_campaign(self, user_id: int, campaign_id: int) -> Optional[Campaign]:
        return self.campaign_repo.get_by_id(user_id, campaign_id)

    def get_campaign_report(self, user_id: int, campaign_id: int) -> Optional[Dict[str, Any]]:
        """Gera relatório detalhado do disparo da campanha com lista de destinatários."""
        campaign = self.campaign_repo.get_by_id(user_id, campaign_id)
        if not campaign:
            return None

        recipients = self.campaign_repo.get_campaign_recipients(campaign_id)
        
        total = campaign.total_recipients
        sent = campaign.total_sent
        failed = campaign.total_failed
        invalid = campaign.total_invalid
        ignored = campaign.total_ignored
        opened = campaign.total_opened or 0
        
        success_rate = 0.0
        if (sent + failed + invalid) > 0:
            success_rate = round((sent / (sent + failed + invalid)) * 100, 1)

        open_rate = 0.0
        if sent > 0:
            open_rate = round((opened / sent) * 100, 1)

        return {
            "campaign": campaign,
            "recipients": recipients,
            "total": total,
            "sent": sent,
            "failed": failed,
            "invalid": invalid,
            "ignored": ignored,
            "opened": opened,
            "open_rate": open_rate,
            "success_rate": success_rate,
            "sent_at": campaign.sent_at.strftime("%d/%m/%Y %H:%M:%S") if campaign.sent_at else "Não disparada"
        }

    def create_campaign(
        self,
        user_id: int,
        name: str,
        subject: str,
        template_id: int,
        contact_ids: Optional[List[int]] = None,
        attachments_meta: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[bool, str, Optional[Campaign]]:
        """Cria uma nova campanha com validação de template e contatos do perfil."""
        name_clean = name.strip() if name else ""
        if not name_clean:
            return False, "O nome da campanha é obrigatório.", None

        subject_clean = subject.strip() if subject else ""
        if not subject_clean:
            return False, "O assunto (Subject) da campanha é obrigatório.", None

        template = self.template_repo.get_by_id(user_id, template_id)
        if not template:
            return False, "Template selecionado não encontrado ou pertence a outro usuário.", None

        # Selecionar contatos especificados ou todos os contatos ativos do perfil
        if contact_ids and len(contact_ids) > 0:
            contacts = self.contact_repo.get_contacts_by_ids(user_id, contact_ids)
        else:
            contacts = self.contact_repo.get_all_active_contacts(user_id)

        if not contacts:
            return False, "Nenhum contato selecionado ou disponível para esta campanha.", None

        campaign = self.campaign_repo.create(
            user_id=user_id,
            name=name_clean,
            subject=subject_clean,
            template_id=template.id,
            contacts=contacts,
            attachments_meta=attachments_meta
        )

        self.log_repo.create_log(
            user_id=user_id,
            action="CAMPANHA_CRIADA",
            description=f"Campanha '{campaign.name}' criada com {len(contacts)} destinatários."
        )

        return True, "Campanha criada com sucesso!", campaign

    def delete_campaign(self, user_id: int, campaign_id: int) -> Tuple[bool, str]:
        """Exclui a campanha e remove fisicamente seus anexos do servidor."""
        campaign = self.campaign_repo.get_by_id(user_id, campaign_id)
        if not campaign:
            return False, "Campanha não encontrada ou não pertence a este perfil."

        # Remover arquivos físicos de anexos
        if campaign.attachments:
            for att in campaign.attachments:
                try:
                    if att.file_path and os.path.exists(att.file_path):
                        os.remove(att.file_path)
                except Exception:
                    pass

        campaign_name = campaign.name
        self.campaign_repo.delete(user_id, campaign_id)

        self.log_repo.create_log(
            user_id=user_id,
            action="CAMPANHA_EXCLUIDA",
            description=f"Campanha '{campaign_name}' (ID {campaign_id}) excluída com sucesso."
        )
        return True, "Campanha excluída com sucesso!"

    def send_campaign(
        self,
        user_id: int,
        campaign_id: int,
        user: User,
        base_url: str = settings.APP_BASE_URL
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executa o disparo da campanha com processamento tolerante a falhas por lote.
        Uma falha em um destinatário não interrompe os demais envios.
        Garante atualização de status mesmo em caso de erro fatal.
        """
        campaign = self.campaign_repo.get_by_id(user_id, campaign_id)
        if not campaign:
            return False, "Campanha não encontrada.", {}

        template = self.template_repo.get_by_id(user_id, campaign.template_id)
        if not template:
            self.campaign_repo.update_campaign_progress(
                campaign_id=campaign.id,
                status=CampaignStatus.FALHA,
                total_sent=0,
                total_failed=0,
                total_invalid=0,
                total_ignored=0
            )
            return False, "Template associado à campanha não foi encontrado.", {}

        # Obter provedor de e-mail configurado para o perfil
        provider, err = self.email_service.get_provider(user_id)
        if not provider:
            self.campaign_repo.update_campaign_progress(
                campaign_id=campaign.id,
                status=CampaignStatus.FALHA,
                total_sent=0,
                total_failed=0,
                total_invalid=0,
                total_ignored=0
            )
            self.log_repo.create_log(
                user_id=user_id,
                action="CAMPANHA_ERRO",
                description=f"Configuração de envio indisponível para campanha '{campaign.name}': {err}"
            )
            return False, f"Configuração de envio indisponível: {err}", {}

        # Garantir status PROCESSANDO no banco
        if campaign.status != CampaignStatus.PROCESSANDO:
            campaign.status = CampaignStatus.PROCESSANDO
            self.db.commit()

        # Obter lista de anexos da campanha
        attachments_list = []
        if campaign.attachments:
            for att in campaign.attachments:
                attachments_list.append({
                    "path": att.file_path,
                    "name": att.file_name,
                    "type": att.content_type
                })

        recipients = self.campaign_repo.get_campaign_recipients(campaign_id)
        
        sent_count = 0
        failed_count = 0
        invalid_count = 0
        ignored_count = 0

        session = None
        try:
            session = provider.get_session()
        except Exception:
            session = None

        final_status = CampaignStatus.CONCLUIDO
        try:
            for r in recipients:
                # 1. Validação de formato de e-mail pré-envio
                is_valid_email, clean_email = SecurityService.validate_email_syntax(r.email)
                if not is_valid_email:
                    invalid_count += 1
                    self.campaign_repo.update_recipient_status(
                        campaign_contact_id=r.id,
                        status=CampaignContactStatus.INVALIDO,
                        error_message=f"E-mail com formato inválido: {r.email}"
                    )
                    continue

                # 2. Verificar status do contato no banco (se cadastrado)
                contact = self.contact_repo.get_by_id(user_id, r.contact_id) if r.contact_id else None
                if contact:
                    if contact.status == ContactStatus.DESCADASTRADO:
                        ignored_count += 1
                        self.campaign_repo.update_recipient_status(
                            campaign_contact_id=r.id,
                            status=CampaignContactStatus.IGNORADO,
                            error_message="Destinatário solicitou descadastro previamente (Opt-out)."
                        )
                        continue
                    elif contact.status == ContactStatus.INATIVO:
                        ignored_count += 1
                        self.campaign_repo.update_recipient_status(
                            campaign_contact_id=r.id,
                            status=CampaignContactStatus.IGNORADO,
                            error_message="Contato está inativo."
                        )
                        continue
                    elif contact.status == ContactStatus.INVALIDO:
                        invalid_count += 1
                        self.campaign_repo.update_recipient_status(
                            campaign_contact_id=r.id,
                            status=CampaignContactStatus.INVALIDO,
                            error_message="Contato marcado como inválido."
                        )
                        continue

                # 3. Montar link de descadastro
                unsubscribe_token = contact.unsubscribe_token if contact else "optout"
                unsubscribe_url = f"{base_url}/unsubscribe?token={unsubscribe_token}"

                # 4. Renderizar e-mail com variáveis personalizadas
                html_body = self.template_service.render_content(
                    header=template.header,
                    body=template.body,
                    footer=template.footer,
                    contact_name=r.name,
                    contact_email=clean_email,
                    company=contact.company if contact else None,
                    profile_name=user.name,
                    unsubscribe_url=unsubscribe_url
                )

                # Injetar pixel invisível de rastreamento de abertura (Open Tracking)
                if getattr(r, "open_token", None):
                    tracking_url = f"{base_url}/track/open/{r.open_token}.png"
                    tracking_tag = f'<img src="{tracking_url}" width="1" height="1" style="display:none !important; max-height:0px; max-width:0px; opacity:0; border:0;" alt="" />'
                    if "</body>" in html_body:
                        html_body = html_body.replace("</body>", f"{tracking_tag}</body>")
                    else:
                        html_body += tracking_tag

                # 5. Realizar o disparo individual via Provider
                send_res = provider.send_email(
                    to_email=clean_email,
                    to_name=r.name,
                    subject=campaign.subject,
                    html_content=html_body,
                    unsubscribe_url=unsubscribe_url,
                    attachments=attachments_list,
                    active_connection=session
                )

                if send_res.success:
                    sent_count += 1
                    self.campaign_repo.update_recipient_status(
                        campaign_contact_id=r.id,
                        status=CampaignContactStatus.ENVIADO
                    )
                else:
                    failed_count += 1
                    self.campaign_repo.update_recipient_status(
                        campaign_contact_id=r.id,
                        status=CampaignContactStatus.FALHA,
                        error_message=send_res.error_message or "Erro desconhecido durante o disparo SMTP."
                    )

                # Atualiza progresso contínuo no banco
                self.campaign_repo.update_campaign_progress(
                    campaign_id=campaign.id,
                    status=CampaignStatus.PROCESSANDO,
                    total_sent=sent_count,
                    total_failed=failed_count,
                    total_invalid=invalid_count,
                    total_ignored=ignored_count
                )

                # Rate limiting de segurança (ativo se configurado e não for mock/teste)
                if not getattr(settings, 'MOCK_EMAIL_SENDING', False) and getattr(settings, 'DEFAULT_RATE_LIMIT_PER_SECOND', 0) > 0 and settings.APP_ENV != "test":
                    time.sleep(1.0 / settings.DEFAULT_RATE_LIMIT_PER_SECOND)

            final_status = CampaignStatus.CONCLUIDO

        except Exception as e:
            final_status = CampaignStatus.FALHA
            self.log_repo.create_log(
                user_id=user_id,
                action="CAMPANHA_ERRO",
                description=f"Erro crítico durante disparo da campanha {campaign.id}: {str(e)}"
            )
        finally:
            if session:
                try:
                    provider.close_session(session)
                except Exception:
                    pass

            now = datetime.now(timezone.utc)
            self.campaign_repo.update_campaign_progress(
                campaign_id=campaign.id,
                status=final_status,
                total_sent=sent_count,
                total_failed=failed_count,
                total_invalid=invalid_count,
                total_ignored=ignored_count,
                sent_at=now
            )

        self.log_repo.create_log(
            user_id=user_id,
            action="CAMPANHA_DISPARADA",
            description=f"Campanha '{campaign.name}' concluída: {sent_count} enviados, {failed_count} falhas, {invalid_count} inválidos, {ignored_count} ignorados."
        )

        report = {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "total_recipients": len(recipients),
            "total_sent": sent_count,
            "total_failed": failed_count,
            "total_invalid": invalid_count,
            "total_ignored": ignored_count,
            "status": final_status
        }

        return True, "Campanha processada com sucesso!", report

    def send_test_email(
        self,
        user_id: int,
        campaign_id: int,
        test_email: str,
        user: User,
        base_url: str = settings.APP_BASE_URL
    ) -> Tuple[bool, str]:
        """
        Envia um e-mail de prova/teste individual para uma caixa de entrada real,
        com prefixo [TESTE] no assunto, interpolação simulada e os anexos da campanha.
        """
        # 1. Validar e-mail de destino
        is_valid, clean_email = SecurityService.validate_email_syntax(test_email)
        if not is_valid:
            return False, f"O e-mail de teste '{test_email}' possui formato inválido."

        # 2. Carregar a campanha
        campaign = self.campaign_repo.get_by_id(user_id, campaign_id)
        if not campaign:
            return False, "Campanha não encontrada ou não pertence ao seu perfil."

        # 3. Carregar o template
        template = self.template_repo.get_by_id(user_id, campaign.template_id)
        if not template:
            return False, "Template associado à campanha não foi encontrado."

        # 4. Obter provedor SMTP
        provider, err = self.email_service.get_provider(user_id)
        if not provider:
            return False, f"Servidor SMTP não configurado ou indisponível: {err}"

        # 5. Lista de anexos reais da campanha
        attachments_list = []
        if campaign.attachments:
            for att in campaign.attachments:
                attachments_list.append({
                    "path": att.file_path,
                    "name": att.file_name,
                    "type": att.content_type
                })

        # 6. Renderizar conteúdo simulado de teste
        test_unsubscribe_url = f"{base_url}/unsubscribe?token=preview_mode"
        html_body = self.template_service.render_content(
            header=template.header,
            body=template.body,
            footer=template.footer,
            contact_name="Destinatário de Teste",
            contact_email=clean_email,
            company="Sua Empresa (Exemplo)",
            profile_name=user.name,
            unsubscribe_url=test_unsubscribe_url
        )

        test_subject = f"[TESTE] {campaign.subject}"

        # 7. Disparo via provedor
        send_res = provider.send_email(
            to_email=clean_email,
            to_name="Destinatário de Teste",
            subject=test_subject,
            html_content=html_body,
            unsubscribe_url=test_unsubscribe_url,
            attachments=attachments_list
        )

        if send_res.success:
            self.log_repo.create_log(
                user_id=user_id,
                action="TESTE_ENVIADO",
                description=f"E-mail de prova da campanha '{campaign.name}' enviado para '{clean_email}'."
            )
            return True, f"E-mail de teste enviado com sucesso para {clean_email}!"
        else:
            return False, f"Falha ao enviar e-mail de teste: {send_res.error_message or 'Erro desconhecido do servidor SMTP.'}"
