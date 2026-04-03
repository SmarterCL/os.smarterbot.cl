from odoo import models, fields, api
from datetime import timedelta
import logging
import requests

_logger = logging.getLogger(__name__)


class EcocuponCoupon(models.Model):
    _name = 'ecocupon.coupon'
    _description = 'EcoCupon Discount Coupon'
    _order = 'create_date desc'

    code = fields.Char(required=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    order_id = fields.Many2one('sale.order', string='Pedido Origen')
    discount_type = fields.Selection([
        ('percentage', 'Porcentaje (%)'),
        ('fixed', 'Monto fijo ($)'),
    ], string='Tipo Descuento', default='percentage')
    discount_value = fields.Float('Valor Descuento', default=10.0)
    expiration_date = fields.Date('Válido Hasta', required=True)
    used = fields.Boolean('Usado', default=False)
    used_order_id = fields.Many2one('sale.order', string='Pedido de Uso')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'El código de cupón debe ser único'),
    ]

    @api.model
    def generate_for_order(self, order):
        """Generar cupón para un pedido confirmado."""
        # Verificar si ya existe uno para este pedido
        existing = self.search([('order_id', '=', order.id)], limit=1)
        if existing:
            return existing

        # Obtener configuración
        ICPSudo = self.env['ir.config_parameter'].sudo()
        discount_type = ICPSudo.get_param('ecocupon_kiosk.discount_type', 'percentage')
        discount_value = float(ICPSudo.get_param('ecocupon_kiosk.discount_value', 10.0))
        validity_days = int(ICPSudo.get_param('ecocupon_kiosk.validity_days', 30))
        emdash_enabled = ICPSudo.get_param('ecocupon_kiosk.emdash_enabled', False)

        # Intentar Emdash para cupón inteligente
        if emdash_enabled:
            try:
                emdash_result = self._call_emdash(order, discount_value)
                if emdash_result:
                    discount_value = emdash_result.get('discount', discount_value)
                    _logger.info(f"EcoCupon Emdash: descuento ajustado a {discount_value}")
            except Exception as e:
                _logger.warning(f"EcoCupon Emdash falló, usando fallback: {e}")

        # Generar código secuencial
        last = self.search([], order='id desc', limit=1)
        next_num = (int(last.code.split('-')[-1]) if last and '-' in last.code else 0) + 1
        code = f"ECO{next_num:04d}"

        # Crear cupón
        coupon = self.create({
            'code': code,
            'partner_id': order.partner_id.id,
            'order_id': order.id,
            'discount_type': discount_type,
            'discount_value': discount_value,
            'expiration_date': fields.Date.today() + timedelta(days=validity_days),
        })

        return coupon

    def _call_emdash(self, order, base_discount):
        """Llamar a Emdash para cupón inteligente basado en historial."""
        try:
            # Contar compras previas del cliente
            prev_orders = self.env['sale.order'].search_count([
                ('partner_id', '=', order.partner_id.id),
                ('state', 'in', ['sale', 'done']),
            ])

            resp = requests.post(
                'http://localhost:8010/generate',
                json={
                    'input': f'Generar cupón para cliente con {prev_orders} compras previas. '
                             f'Compra actual: {order.amount_total}. '
                             f'Descuento base: {base_discount}%. '
                             f'Responder solo con un número de descuento (5-25).',
                    'context': 'checkout_coupon',
                },
                timeout=2
            )
            if resp.status_code == 200:
                data = resp.json()
                text = data.get('text', '')
                # Extraer número
                import re
                numbers = re.findall(r'\d+', text)
                if numbers:
                    discount = min(max(int(numbers[0]), 5), 25)
                    return {'discount': discount}
        except Exception:
            pass
        return None

    def apply_coupon(self, order):
        """Aplicar cupón a un pedido (para próxima compra)."""
        if self.used:
            return {'error': 'Cupón ya usado'}
        if self.expiration_date < fields.Date.today():
            return {'error': 'Cupón expirado'}
        if self.partner_id != order.partner_id:
            return {'error': 'Cupón no pertenece a este cliente'}

        # Aplicar descuento
        if self.discount_type == 'percentage':
            discount_amount = order.amount_total * self.discount_value / 100
        else:
            discount_amount = min(self.discount_value, order.amount_total)

        self.used = True
        self.used_order_id = order.id

        return {
            'success': True,
            'discount': discount_amount,
            'code': self.code,
        }
