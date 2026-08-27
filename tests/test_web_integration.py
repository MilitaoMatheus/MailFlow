import pytest
from app.models.contact import ContactStatus
from app.models.campaign import CampaignStatus
from app.services.auth_service import AuthService
from app.services.contact_service import ContactService


def test_full_web_flow_user_journey(client):
    """
    Testa a jornada completa do usuário via requisições HTTP reais:
    Registro -> Login -> Configurar SMTP -> Cadastrar Contato -> Importar CSV -> Criar Template -> Criar e Disparar Campanha -> Relatório.
    """
    # 1. Registro do Usuário
    reg_resp = client.post(
        "/register",
        data={"name": "Lucas Dev", "email": "lucas.dev@empresa.com", "password": "superpassword123"},
        follow_redirects=False
    )
    assert reg_resp.status_code == 303
    assert reg_resp.headers["location"] == "/dashboard"
    assert "session_token" in reg_resp.cookies

    # 2. Configurar SMTP
    smtp_resp = client.post(
        "/settings/email",
        data={
            "sender_name": "Lucas Dev",
            "email": "lucas.dev@empresa.com",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": "587",
            "smtp_username": "lucas.dev@empresa.com",
            "smtp_password": "app-password-xyz",
            "smtp_security": "STARTTLS"
        },
        follow_redirects=False
    )
    assert smtp_resp.status_code == 303

    # 3. Cadastrar Contato
    contact_resp = client.post(
        "/contacts/new",
        data={
            "name": "Cliente VIP",
            "email": "vip@cliente.com",
            "company": "VIP Corp",
            "phone": "11999998888",
            "contact_status": "ATIVO"
        },
        follow_redirects=False
    )
    assert contact_resp.status_code == 303

    # 4. Importar CSV
    csv_payload = "nome;email;empresa;telefone\nBeatriz;beatriz@loja.com;Loja B;11911112222\nPedro;pedro@loja.com;Loja P;11933334444\n"
    import_resp = client.post(
        "/contacts/import",
        files={"file": ("contatos.csv", csv_payload.encode("utf-8"), "text/csv")}
    )
    assert import_resp.status_code == 200
    assert "Processamento Concluído" in import_resp.text

    # 5. Exportar CSV
    export_resp = client.get("/contacts/export")
    assert export_resp.status_code == 200
    assert "vip@cliente.com" in export_resp.text
    assert "beatriz@loja.com" in export_resp.text

    # 6. Criar Template Particionado
    tpl_resp = client.post(
        "/templates/new",
        data={
            "name": "Template Promocional",
            "header": "<h1>Ofertas {{empresa}}</h1>",
            "body": "<p>Olá {{nome}}, temos novidades para você!</p>",
            "footer": "<p><a href='{{link_descadastro}}'>Sair</a></p>"
        },
        follow_redirects=False
    )
    assert tpl_resp.status_code == 303

    # 7. Criar Campanha
    camp_resp = client.post(
        "/campaigns/new",
        data={
            "name": "Campanha Inaugural",
            "subject": "Super Novidade!",
            "template_id": 1,
            "recipient_type": "all"
        },
        follow_redirects=False
    )
    assert camp_resp.status_code == 303
    assert "/campaigns/1" in camp_resp.headers["location"]

    # 8. Visualizar Relatório da Campanha
    view_camp = client.get("/campaigns/1")
    assert view_camp.status_code == 200
    assert "Campanha Inaugural" in view_camp.text
    assert "Super Novidade!" in view_camp.text
    assert "vip@cliente.com" in view_camp.text

    # 9. Dashboard exibe os dados atualizados
    dash_resp = client.get("/dashboard")
    assert dash_resp.status_code == 200
    assert "Campanhas" in dash_resp.text
    assert "Contatos" in dash_resp.text


def test_http_route_protection_and_cross_user_isolation(client, db_session, user_a, user_b):
    """
    Testa se o Usuário A tentar editar recursos de B via HTTP recebe erro/rejeição sem alterar dados de B.
    """
    contact_service = ContactService(db_session)

    # Maria (User B) cria um contato
    _, _, contact_b = contact_service.create_contact(
        user_id=user_b.id,
        name="Contato Original da Maria",
        email="maria.secret@empresa.com"
    )

    # Autenticar cliente como João (User A)
    token_a = AuthService.create_session_token(user_a.id)
    client.cookies.set("session_token", token_a)

    # João tenta editar o contato de Maria fazendo POST para /contacts/{contact_b.id}/edit
    hack_resp = client.post(
        f"/contacts/{contact_b.id}/edit",
        data={
            "name": "Contato Hackeado",
            "email": "hacked@empresa.com",
            "contact_status": "ATIVO"
        },
        follow_redirects=False
    )
    # Deve retornar erro 400
    assert hack_resp.status_code == 400
    assert "não encontrado" in hack_resp.text.lower()

    # João tenta deletar o contato de Maria fazendo POST para /contacts/{contact_b.id}/delete
    del_resp = client.post(
        f"/contacts/{contact_b.id}/delete",
        follow_redirects=False
    )

    # Verificar que os dados de Maria continuam 100% intactos no banco de dados
    db_session.refresh(contact_b)
    assert contact_b.name == "Contato Original da Maria"
    assert contact_b.email == "maria.secret@empresa.com"
