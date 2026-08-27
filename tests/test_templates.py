from app.services.template_service import TemplateService


def test_template_variable_substitution():
    """Testa renderização e substituição de tags e variáveis dinâmicas nos templates."""
    header = "<header>Logo: {{empresa}}</header>"
    body = "<h1>Olá, {{nome}}!</h1><p>Seu e-mail cadastrado é {{email}}.</p><p>Equipe: {{nome_perfil}}</p>"
    footer = "<footer>Data: {{data}} | <a href='{{link_descadastro}}'>Descadastrar</a></footer>"

    html = TemplateService.render_content(
        header=header,
        body=body,
        footer=footer,
        contact_name="Fernanda Lima",
        contact_email="fernanda@cliente.com",
        company="Empresa Beta",
        profile_name="João Vendedor",
        unsubscribe_url="http://localhost:8000/unsubscribe?token=abc-123-xyz"
    )

    assert "Logo: Empresa Beta" in html
    assert "Olá, Fernanda Lima!" in html
    assert "Seu e-mail cadastrado é fernanda@cliente.com." in html
    assert "Equipe: João Vendedor" in html
    assert "http://localhost:8000/unsubscribe?token=abc-123-xyz" in html
    assert "class=\"email-container\"" in html
    assert "<!DOCTYPE html>" in html


def test_template_fallback_when_vars_missing():
    """Testa substituição limpa quando valores opcionais estão ausentes."""
    body = "Olá, {{nome}} da empresa {{empresa}}!"
    html = TemplateService.render_content(
        header="",
        body=body,
        footer="",
        contact_name="",
        contact_email="test@test.com",
        company=None,
        profile_name=None,
        unsubscribe_url=None
    )

    assert "Olá, Cliente" in html
