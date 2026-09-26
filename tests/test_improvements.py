import os
import tempfile
import pytest
from app.services.security_service import SecurityService
from app.services.auth_service import AuthService
from app.services.template_service import TemplateService
from app.services.contact_service import ContactService
from app.services.campaign_service import CampaignService
from app.models.campaign import CampaignStatus
from app.models.user import User


def test_xss_sanitization_in_templates(db_session, user_a):
    """Garante que tags HTML/script em variáveis dinâmicas sejam escapadas contra ataques XSS."""
    template_service = TemplateService(db_session)
    malicious_name = "<script>alert('XSS')</script>"
    malicious_company = '<b onmouseover="alert(1)">Empresa</b>'

    html = template_service.render_content(
        header="<p>Header</p>",
        body="<p>Olá, {{nome}} da {{empresa}}</p>",
        footer="<p>Footer</p>",
        contact_name=malicious_name,
        contact_email="alvo@teste.com",
        company=malicious_company,
        profile_name=user_a.name
    )

    # Não deve conter tags raw não escapadas
    assert "<script>" not in html
    assert "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;" in html or "&lt;script&gt;alert('XSS')&lt;/script&gt;" in html
    assert "<b onmouseover" not in html
    assert "&lt;b onmouseover=&quot;alert(1)&quot;&gt;Empresa&lt;/b&gt;" in html or "&lt;b onmouseover=" in html


def test_filename_sanitization():
    """Garante que tentativas de Path Traversal no upload sejam neutralizadas."""
    assert SecurityService.sanitize_filename("../../etc/passwd") == "passwd"
    assert SecurityService.sanitize_filename("..\\..\\windows\\system32.dll") == "system32.dll"
    assert SecurityService.sanitize_filename("arquivo teste (1) [novo].pdf") == "arquivo_teste__1___novo_.pdf"
    assert SecurityService.sanitize_filename("") == "arquivo"
    assert SecurityService.sanitize_filename("...hidden") == "hidden"


def test_session_invalidation_on_password_change(db_session, user_a):
    """Garante que a troca de senha invalida tokens de sessão emitidos anteriormente."""
    auth_service = AuthService(db_session)

    # 1. Cria token para o usuário com a versão inicial (1)
    old_token = auth_service.create_session_token(user_a.id, token_version=user_a.token_version)
    payload_before = auth_service.decode_session_payload(old_token)
    assert payload_before is not None
    assert payload_before["ver"] == user_a.token_version

    # 2. Altera a senha do usuário
    ok, msg = auth_service.change_password(user_a.id, current_password="senha123", new_password="novaSenhaForte99")
    assert ok is True

    # 3. Verifica que a versão do token do usuário foi incrementada no banco
    db_session.refresh(user_a)
    assert user_a.token_version == 2

    # 4. O token antigo tem ver=1, enquanto o usuário agora exige ver=2
    payload_old = auth_service.decode_session_payload(old_token)
    assert payload_old["ver"] == 1
    assert payload_old["ver"] != user_a.token_version  # Sessão antiga invalidada!

    # 5. Um novo token gerado pós-troca tem ver=2
    new_token = auth_service.create_session_token(user_a.id, token_version=user_a.token_version)
    payload_new = auth_service.decode_session_payload(new_token)
    assert payload_new["ver"] == user_a.token_version == 2


def test_fast_bulk_csv_import(db_session, user_a):
    """Testa a nova importação de contatos em lote com detecção instantânea de duplicidades."""
    contact_service = ContactService(db_session)

    csv_data = """nome;email;empresa;telefone
Cliente 1;cliente1@teste.com;Empresa A;11999999991
Cliente 2;cliente2@teste.com;Empresa B;11999999992
Cliente 3;cliente3@teste.com;Empresa C;11999999993
Cliente Duplicado;cliente1@teste.com;Empresa A;11999999991
Cliente Invalido;email_invalido_sem_arroba;Empresa D;11999999994
Cliente 4;cliente4@teste.com;Empresa E;11999999995
"""
    result = contact_service.import_csv(user_a.id, csv_data)
    assert result["imported"] == 4
    assert result["duplicates"] == 1
    assert result["invalid"] == 1

    # Segunda importação com os mesmos dados deve detectar todos os 5 e-mails como duplicados
    result_dup = contact_service.import_csv(user_a.id, csv_data)
    assert result_dup["imported"] == 0
    assert result_dup["duplicates"] == 5
    assert result_dup["invalid"] == 1


def test_campaign_status_and_deletion(db_session, user_a, client):
    """Testa o endpoint de status em tempo real da campanha e exclusão com limpeza de anexos físicos."""
    campaign_service = CampaignService(db_session)
    template_service = TemplateService(db_session)
    contact_service = ContactService(db_session)

    # 1. Cria template e contatos
    _, _, template = template_service.create_template(
        user_id=user_a.id,
        name="Template Status Test",
        header="<h1>Header</h1>",
        body="<p>Corpo</p>",
        footer="<p>Rodapé</p>"
    )
    _, _, contact = contact_service.create_contact(
        user_id=user_a.id,
        name="Contato Teste",
        email="contato@status.com"
    )

    # 2. Cria arquivo temporário simulando anexo
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(b"%PDF-1.4 dummy content")
        temp_file_path = f.name

    assert os.path.exists(temp_file_path)

    # 3. Cria campanha com o anexo
    _, _, campaign = campaign_service.create_campaign(
        user_id=user_a.id,
        name="Campanha Para Deletar",
        subject="Assunto Teste",
        template_id=template.id,
        contact_ids=[contact.id],
        attachments_meta=[{
            "file_path": temp_file_path,
            "file_name": "dummy.pdf",
            "content_type": "application/pdf"
        }]
    )
    assert campaign is not None

    # 4. Autentica no cliente de teste
    token = AuthService.create_session_token(user_a.id, token_version=user_a.token_version)
    client.cookies.set("session_token", token)

    # 5. Testa API de status JSON
    res_status = client.get(f"/campaigns/{campaign.id}/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["id"] == campaign.id
    assert status_data["total"] == 1
    assert "progress_pct" in status_data

    # 6. Exclui a campanha via rota POST
    res_del = client.post(f"/campaigns/{campaign.id}/delete", follow_redirects=False)
    assert res_del.status_code == 303

    # 7. Verifica que a campanha foi removida do banco
    deleted_campaign = campaign_service.get_campaign(user_a.id, campaign.id)
    assert deleted_campaign is None

    # 8. Verifica que o anexo físico no disco foi devidamente removido
    assert not os.path.exists(temp_file_path)
