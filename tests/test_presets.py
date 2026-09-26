import pytest
from app.services.preset_templates import get_all_presets, get_preset_by_id, compile_preset_html
from app.services.template_service import TemplateService
from app.models.template import Template


def test_preset_list_and_details():
    """Garante que todos os modelos pré-definidos estão configurados e acessíveis."""
    presets = get_all_presets()
    assert len(presets) == 5

    preset_ids = [p["id"] for p in presets]
    assert "newsletter" in preset_ids
    assert "promocao" in preset_ids
    assert "comunicado" in preset_ids
    assert "boas_vindas" in preset_ids
    assert "evento" in preset_ids

    for p in presets:
        assert "name" in p
        assert "brand_color" in p
        assert "header_style" in p
        assert "headline" in p
        assert "message" in p
        assert "btn_text" in p
        assert "btn_url" in p
        assert "footer_note" in p

    # Teste de busca por ID
    promo = get_preset_by_id("promocao")
    assert promo["id"] == "promocao"
    assert promo["brand_color"] == "#ea580c"

    # Teste de fallback para ID inexistente
    fallback = get_preset_by_id("nao_existe")
    assert fallback["id"] == "newsletter"


def test_compile_preset_html_custom_colors_and_cta():
    """Valida a compilação do construtor semântico em HTML compatível com e-mails."""
    header, body, footer = compile_preset_html(
        header_title="ACME SHOP",
        header_subtitle="Super Oferta Exclusiva",
        headline="Desconto Especial de 30%",
        greeting="Olá, {{nome}}!",
        message="Aproveite esta condição única no nosso site.\n\nMais uma linha de conteúdo.",
        btn_text="Ver Ofertas Agora",
        btn_url="https://acmeshop.com.br/promocao",
        footer_note="Oferta válida enquanto durarem os estoques.",
        brand_color="#059669",
        header_style="brand"
    )

    # 1. Validações do Cabeçalho
    assert "ACME SHOP" in header
    assert "Super Oferta Exclusiva" in header
    assert "background-color: #059669" in header

    # 2. Validações do Corpo
    assert "Olá, {{nome}}!" in body
    assert "Desconto Especial de 30%" in body
    assert "Aproveite esta condição única" in body
    assert "<p style=" in body
    assert "Ver Ofertas Agora" in body
    assert "https://acmeshop.com.br/promocao" in body
    assert "background-color: #059669" in body  # Cor do botão sincronizada

    # 3. Validações do Rodapé
    assert "Oferta válida enquanto durarem os estoques." in footer
    assert "{{link_descadastro}}" in footer
    assert "color: #059669" in footer  # Cor do link de descadastro sincronizada


def test_compile_preset_html_light_header_and_empty_cta():
    """Valida compilação com cabeçalho claro e sem botão CTA."""
    header, body, footer = compile_preset_html(
        header_title="Comunicado",
        header_subtitle="Aviso do RH",
        headline="Manutenção Programada",
        greeting="Prezado(a),",
        message="Nosso sistema passará por manutenção neste domingo.",
        btn_text="",
        btn_url="",
        footer_note="Setor de Infraestrutura",
        brand_color="#0284c7",
        header_style="light"
    )

    assert "background-color: #ffffff" in header
    assert "border-bottom: 1px solid #e2e8f0" in header
    assert "Manutenção Programada" in body
    assert "<a href=" not in body  # Botão CTA omitido


def test_templates_index_endpoint_shows_presets(client_user_a):
    """Garante que a página de templates renderiza o banner de modelos e o modal de suporte."""
    response = client_user_a.get("/templates")
    assert response.status_code == 200
    html = response.text

    assert "Comece com um Modelo Pronto" in html
    assert "Template sob Medida" in html
    assert "Solicitar Template Personalizado" in html
    assert "WhatsApp Comercial" in html
    assert "suporte@mailflow.com.br" in html
    assert "Newsletter / Resumo Semanal" in html
    assert "Oferta Comercial / Promoção" in html


def test_templates_new_endpoint_with_preset(client_user_a):
    """Garante que a tela de criação carrega os dados do preset selecionado sem modo HTML."""
    response = client_user_a.get("/templates/new?preset_id=promocao")
    assert response.status_code == 200
    html = response.text

    assert "Criador de Templates" in html
    assert "Construtor Visual Sem Código" in html
    assert "Modo HTML Avançado" not in html
    assert "Pedir Template sob Medida" in html
    assert "Prévia ao Vivo" in html
    assert "overflow-y-auto" in html
    assert "templateBuilder()" in html


def test_create_and_render_template_from_preset(client_user_a, db_session, user_a):
    """Testa criação completa via POST de um template compilado e sua subsequente renderização final."""
    header, body, footer = compile_preset_html(
        header_title="Clube VIP",
        header_subtitle="Edição de Aniversário",
        headline="Você Ganhou um Presente",
        greeting="Olá, {{nome}}!",
        message="Preparamos um desconto imperdível para a empresa {{empresa}}.",
        btn_text="Resgatar Presente",
        btn_url="https://clube.com.br/resgatar",
        footer_note="Válido hoje.",
        brand_color="#7c3aed",
        header_style="brand"
    )

    response = client_user_a.post(
        "/templates/new",
        data={
            "name": "Template VIP Aniversário",
            "header": header,
            "body": body,
            "footer": footer
        },
        follow_redirects=False
    )
    assert response.status_code == 303

    # Verifica se foi gravado no banco
    created = db_session.query(Template).filter(
        Template.user_id == user_a.id,
        Template.name == "Template VIP Aniversário"
    ).first()
    assert created is not None
    assert "Clube VIP" in created.header
    assert "Resgatar Presente" in created.body

    # Renderiza para cliente final
    rendered_email = TemplateService.render_content(
        header=created.header,
        body=created.body,
        footer=created.footer,
        contact_name="Carlos Drummond",
        contact_email="carlos@letras.com.br",
        company="Poesia & Cia",
        profile_name=user_a.name,
        unsubscribe_url="http://localhost:8000/unsubscribe?token=teste-123"
    )

    assert "Clube VIP" in rendered_email
    assert "Olá, Carlos Drummond!" in rendered_email
    assert "Poesia &amp; Cia" in rendered_email or "Poesia & Cia" in rendered_email
    assert "http://localhost:8000/unsubscribe?token=teste-123" in rendered_email
    assert "João Silva" in rendered_email


def test_edit_template_loads_form(client_user_a, db_session, user_a):
    """Garante que a rota de edição de template carrega o formulário com sucesso."""
    template = Template(
        user_id=user_a.id,
        name="Template Antigo",
        header="<div>Topo</div>",
        body="<p>Corpo</p>",
        footer="<div>Fim</div>"
    )
    db_session.add(template)
    db_session.commit()

    response = client_user_a.get(f"/templates/{template.id}/edit")
    assert response.status_code == 200
    html = response.text
    assert "Editar Template" in html
    assert "Template Antigo" in html
