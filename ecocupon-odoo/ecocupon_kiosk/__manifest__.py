{
    "name": "EcoCupon Kiosk",
    "version": "1.0.0",
    "category": "Sales/Point of Sale",
    "summary": "Genera cupones automáticos en checkout + modo kiosk vertical + Flow.cl",
    "description": """
EcoCupon Kiosk
==============
Módulo de quiosco vertical para Odoo con:
- Cupón automático al confirmar pedido
- Pantalla kiosk vertical (480px)
- Integración Flow.cl para pagos
- Cupón visible en checkout final
    """,
    "author": "SmarterOS",
    "website": "https://os.smarterbot.store",
    "license": "LGPL-3",
    "depends": ["sale", "sale_coupon", "website_sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/ecocupon_templates.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ecocupon_kiosk/static/src/css/kiosk.css",
            "ecocupon_kiosk/static/src/js/kiosk_checkout.js",
        ],
    },
    "installable": True,
    "application": False,
}
