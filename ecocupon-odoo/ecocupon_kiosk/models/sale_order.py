from odoo import models, fields, api
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ecocupon_generated = fields.Boolean('Cupón EcoCupon Generado', default=False)
    ecocupon_code = fields.Char('Código Cupón', readonly=True)

    def action_confirm(self):
        """Al confirmar el pedido, generar cupón automático para próxima compra."""
        res = super().action_confirm()
        for order in self:
            if order.ecocupon_generated:
                continue
            if not order.partner_id:
                continue

            # Generar cupón
            coupon = self.env['ecocupon.coupon'].generate_for_order(order)
            if coupon:
                order.ecocupon_generated = True
                order.ecocupon_code = coupon.code
                _logger.info(
                    f"EcoCupon: Cupón {coupon.code} generado para pedido {order.name} "
                    f"(cliente: {order.partner_id.name})"
                )

        return res


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ecocupon_enabled = fields.Boolean(
        'Activar EcoCupon',
        config_parameter='ecocupon_kiosk.enabled',
        default=True
    )
    ecocupon_discount_type = fields.Selection([
        ('percentage', 'Porcentaje (%)'),
        ('fixed', 'Monto fijo ($)'),
    ], string='Tipo Descuento', config_parameter='ecocupon_kiosk.discount_type', default='percentage')
    ecocupon_discount_value = fields.Float(
        'Valor Descuento',
        config_parameter='ecocupon_kiosk.discount_value',
        default=10.0
    )
    ecocupon_validity_days = fields.Integer(
        'Días de Validez',
        config_parameter='ecocupon_kiosk.validity_days',
        default=30
    )
    ecocupon_emdash_enabled = fields.Boolean(
        'Usar Emdash (IA)',
        config_parameter='ecocupon_kiosk.emdash_enabled',
        default=False,
        help='Si Emdash está activo, genera cupones inteligentes basados en historial"
    )
