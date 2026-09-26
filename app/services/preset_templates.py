from typing import Dict, Any, List, Tuple


PRESET_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "newsletter",
        "name": "Newsletter / Resumo Semanal",
        "icon": "newspaper",
        "badge": "Mais Popular",
        "description": "Ideal para envio de novidades, artigos, resumos da semana e dicas da sua área.",
        "brand_color": "#2563EB",
        "header_style": "dark",
        "header_title": "{{empresa}}",
        "header_subtitle": "Edição Semanal • Novidades & Conteúdos",
        "greeting": "Olá, {{nome}}!",
        "headline": "O que você precisa saber esta semana",
        "message": "Separamos para você os principais destaques, novidades do nosso setor e dicas práticas para aplicar no seu dia a dia.\n\nNesta edição, exploramos novas tendências e como você pode extrair o máximo de produtividade com as melhores ferramentas do mercado.",
        "btn_text": "Ler Artigo Completo no Blog",
        "btn_url": "https://seusite.com.br/blog",
        "footer_note": "Você está recebendo esta newsletter porque é um contato cadastrado na nossa comunidade."
    },
    {
        "id": "promocao",
        "name": "Oferta Comercial / Promoção",
        "icon": "tag",
        "badge": "Alta Conversão",
        "description": "Perfeito para lançamentos de produtos, descontos imperdíveis e oportunidades por tempo limitado.",
        "brand_color": "#ea580c",
        "header_style": "brand",
        "header_title": "OFERTA EXCLUSIVA",
        "header_subtitle": "Condição especial válida por tempo limitado",
        "greeting": "Olá, {{nome}}!",
        "headline": "Condição Especial Reservada para {{empresa}}",
        "message": "Temos uma grande novidade para você: preparamos um desconto imperdível nos nossos principais planos e soluções.\n\nGaranta acesso imediato com suporte prioritário e condições que não se repetirão este ano. Essa oferta expira em breve!",
        "btn_text": "Aproveitar Desconto Agora",
        "btn_url": "https://seusite.com.br/oferta",
        "footer_note": "Promoção válida por tempo limitado ou enquanto durarem as vagas disponíveis."
    },
    {
        "id": "comunicado",
        "name": "Comunicado Oficial / Aviso",
        "icon": "bell",
        "badge": "Corporativo",
        "description": "Estilo sóbrio e direto para avisos formais, manutenções, políticas e comunicados internos.",
        "brand_color": "#0284c7",
        "header_style": "light",
        "header_title": "COMUNICADO OFICIAL",
        "header_subtitle": "Atualização importante sobre nossos serviços",
        "greeting": "Prezado(a) {{nome}},",
        "headline": "Informações Importantes sobre Nossa Operação",
        "message": "Gostaríamos de informar sobre uma atualização importante em nossas plataformas e rotinas de atendimento.\n\nNossa equipe segue empenhada em entregar a melhor experiência contínua com máxima segurança, transparência e estabilidade para todos os parceiros.",
        "btn_text": "Acessar Portal do Cliente",
        "btn_url": "https://seusite.com.br/portal",
        "footer_note": "Mensagem oficial enviada pelo setor de comunicação e compliance."
    },
    {
        "id": "boas_vindas",
        "name": "Boas-Vindas / Onboarding",
        "icon": "sparkles",
        "badge": "Relacionamento",
        "description": "Apresentação calorosa com passos rápidos para novos clientes ou assinantes.",
        "brand_color": "#059669",
        "header_style": "brand",
        "header_title": "SEJA MUITO BEM-VINDO(A)!",
        "header_subtitle": "Estamos muito felizes em ter você aqui",
        "greeting": "Olá, {{nome}}! É um prazer ter você conosco.",
        "headline": "Seus Primeiros Passos Conosco",
        "message": "Parabéns por dar este passo importante com a gente! Nossa missão é garantir que você atinja seus objetivos de forma rápida e segura.\n\nPara começar com o pé direito, preparamos um guia passo a passo para você configurar sua conta e aproveitar todas as funcionalidades.",
        "btn_text": "Começar Agora",
        "btn_url": "https://seusite.com.br/comece-aqui",
        "footer_note": "Se precisar de qualquer auxílio inicial, responda diretamente a este e-mail."
    },
    {
        "id": "evento",
        "name": "Convite para Evento / Reunião",
        "icon": "calendar",
        "badge": "Eventos",
        "description": "Foco em data, detalhes do encontro e confirmação de presença (RSVP).",
        "brand_color": "#7c3aed",
        "header_style": "dark",
        "header_title": "CONVITE ESPECIAL",
        "header_subtitle": "Encontro exclusivo para parceiros",
        "greeting": "Olá, {{nome}}, tudo bem?",
        "headline": "Você é nosso convidado especial",
        "message": "Temos a satisfação de convidá-lo(a) para o nosso próximo encontro online exclusivo.\n\nData: Quinta-feira • Horário: 19h00 (Horário de Brasília)\nTema: Inovações e Melhores Práticas para o seu Negócio.\n\nAs vagas são limitadas para podermos interagir com todos os participantes.",
        "btn_text": "Confirmar Minha Presença",
        "btn_url": "https://seusite.com.br/evento",
        "footer_note": "A transmissão acontecerá ao vivo com link restrito aos inscritos confirmados."
    }
]


def get_all_presets() -> List[Dict[str, Any]]:
    """Retorna a lista de todos os modelos prontos disponíveis."""
    return PRESET_TEMPLATES


def get_preset_by_id(preset_id: str) -> Dict[str, Any]:
    """Retorna um modelo pronto pelo ID ou o primeiro como fallback."""
    for p in PRESET_TEMPLATES:
        if p["id"] == preset_id:
            return p
    return PRESET_TEMPLATES[0]


def compile_preset_html(
    header_title: str,
    header_subtitle: str,
    headline: str,
    greeting: str,
    message: str,
    btn_text: str,
    btn_url: str,
    footer_note: str,
    brand_color: str = "#2563EB",
    header_style: str = "dark"
) -> Tuple[str, str, str]:
    """
    Compila os campos semânticos preenchidos pelo usuário em blocos de Header, Body e Footer limpos.
    Gera código HTML perfeitamente compatível com clientes de e-mail (estilos inline e responsivos).
    """
    # 1. Definir cores do Cabeçalho
    if header_style == "brand":
        header_bg = brand_color
        title_color = "#ffffff"
        sub_color = "#f1f5f9"
        border_style = ""
    elif header_style == "light":
        header_bg = "#ffffff"
        title_color = "#0f172a"
        sub_color = "#64748b"
        border_style = "border-bottom: 1px solid #e2e8f0;"
    else:  # dark
        header_bg = "#0f172a"
        title_color = "#ffffff"
        sub_color = "#94a3b8"
        border_style = ""

    # Montagem do HEADER
    header_html = f"""<div style="margin: -24px; padding: 28px 24px; background-color: {header_bg}; {border_style} text-align: center;">
  <h1 style="margin: 0; font-size: 22px; font-weight: 800; color: {title_color}; letter-spacing: 0.5px;">{header_title or '{{empresa}}'}</h1>
  {f'<p style="margin: 6px 0 0 0; font-size: 13px; color: {sub_color};">{header_subtitle}</p>' if header_subtitle else ''}
</div>"""

    # Formatar quebras de linha da mensagem em parágrafos HTML
    paragraphs = []
    for block in (message or "").split("\n\n"):
        clean_block = block.strip().replace("\n", "<br>")
        if clean_block:
            paragraphs.append(f'<p style="margin: 0 0 16px 0; font-size: 15px; line-height: 1.6; color: #334155;">{clean_block}</p>')
    body_paragraphs = "\n".join(paragraphs)

    # Montagem do Botão de Ação (CTA)
    btn_html = ""
    if btn_text and btn_url:
        btn_html = f"""<div style="text-align: center; margin: 32px 0 24px 0;">
  <a href="{btn_url}" style="background-color: {brand_color}; color: #ffffff; display: inline-block; padding: 13px 28px; font-size: 14px; font-weight: 700; text-decoration: none; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); letter-spacing: 0.3px;">
    {btn_text} &rarr;
  </a>
</div>"""

    # Montagem do BODY
    greeting_html = f'<p style="margin: 0 0 14px 0; font-size: 16px; font-weight: 600; color: {brand_color};">{greeting}</p>' if greeting else ''
    headline_html = f'<h2 style="margin: 0 0 20px 0; font-size: 20px; font-weight: 800; color: #0f172a; line-height: 1.3;">{headline}</h2>' if headline else ''

    body_html = f"""{greeting_html}
{headline_html}
{body_paragraphs}
{btn_html}
<p style="margin: 24px 0 0 0; font-size: 14px; color: #64748b; line-height: 1.5;">
  Atenciosamente,<br>
  <strong style="color: #0f172a;">{{{{nome_perfil}}}}</strong>
</p>"""

    # Montagem do FOOTER
    footer_note_html = f'<p style="margin: 0 0 8px 0; font-size: 12px; color: #64748b;">{footer_note}</p>' if footer_note else ''
    footer_html = f"""{footer_note_html}
<p style="margin: 0 0 12px 0; font-size: 12px; color: #94a3b8;">
  <strong>{{{{empresa}}}}</strong> &bull; Enviado em {{{{data}}}}
</p>
<p style="margin: 0; font-size: 11px; color: #94a3b8;">
  Não deseja mais receber estes e-mails? 
  <a href="{{{{link_descadastro}}}}" style="color: {brand_color}; text-decoration: underline; font-weight: 500;">Cancelar inscrição</a>
</p>"""

    return header_html, body_html, footer_html
