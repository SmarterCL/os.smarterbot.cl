from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class EcocuponController(http.Controller):

    @http.route('/ecocupon/last_coupon', type='json', auth='user')
    def last_coupon(self):
        """Obtener último cupón activo del cliente."""
        partner = request.env.user.partner_id
        coupon = request.env['ecocupon.coupon'].search(
            [
                ('partner_id', '=', partner.id),
                ('used', '=', False),
                ('active', '=', True),
            ],
            order='create_date desc',
            limit=1
        )
        if coupon:
            return {
                'coupon_code': coupon.code,
                'discount': coupon.discount_value,
                'discount_type': coupon.discount_type,
                'expiration_date': coupon.expiration_date.strftime('%d/%m/%Y'),
            }
        return {'coupon_code': None}

    @http.route('/ecocupon/emdash_coupon', type='json', auth='user')
    def emdash_coupon(self):
        """Obtener cupón inteligente via Emdash con fallback."""
        partner = request.env.user.partner_id

        # Intentar Emdash primero
        try:
            resp = request.env['ecocupon.coupon']._call_emdash(
                request.env['sale.order'].browse(),
                10.0
            )
            if resp and resp.get('discount'):
                return {
                    'coupon_code': 'ECOSMART',
                    'discount': resp['discount'],
                    'source': 'emdash',
                }
        except Exception as e:
            _logger.warning(f"EcoCupon Emdash fallback: {e}")

        # Fallback: último cupón
        coupon = request.env['ecocupon.coupon'].search(
            [
                ('partner_id', '=', partner.id),
                ('used', '=', False),
                ('active', '=', True),
            ],
            order='create_date desc',
            limit=1
        )
        if coupon:
            return {
                'coupon_code': coupon.code,
                'discount': coupon.discount_value,
                'source': 'database',
            }
        return {'coupon_code': None}

    @http.route('/ecocupon/apply', type='json', auth='user')
    def apply_coupon(self, coupon_code):
        """Aplicar cupón al carrito actual."""
        order = request.website.sale_get_order()
        coupon = request.env['ecocupon.coupon'].search(
            [('code', '=', coupon_code)], limit=1
        )
        if not coupon:
            return {'error': 'Cupón no encontrado'}

        result = coupon.apply_coupon(order)
        if result.get('success'):
            order._cart_update(
                product_id=order.pricelist_id.discount_product_id.id if hasattr(order.pricelist_id, 'discount_product_id') else None,
                add_qty=0,
            )
            # Aplicar descuento como línea de orden
            order.order_line.filtered(
                lambda l: l.is_delivery or l.product_id.type == 'service'
            ).write({'discount': coupon.discount_value})

        return result

    @http.route('/ecocupon/checkout', type='http', auth='public', website=True)
    def checkout_with_coupon(self, **kw):
        """Checkout con banner de cupón visible."""
        partner = request.env.user.partner_id if request.env.user._is_public() == False else None
        coupon = None
        if partner:
            coupon = request.env['ecocupon.coupon'].search(
                [
                    ('partner_id', '=', partner.id),
                    ('used', '=', False),
                    ('active', '=', True),
                ],
                order='create_date desc',
                limit=1
            )

        return request.render('ecocupon_kiosk.checkout_coupon_banner', {
            'coupon': coupon,
            'order': request.website.sale_get_order(),
        })

    @http.route('/ecocupon/flow_webhook', type='http', auth='public', csrf=False)
    def flow_webhook(self, **kw):
        """Webhook de Flow.cl para confirmación de pago."""
        # Flow.cl envía: token, request_date, buyer_email, amount, commerce_order
        _logger.info(f"Flow.cl webhook: {kw}")

        # Verificar firma (implementar según docs de Flow.cl)
        # Buscar pedido por commerce_order
        order = request.env['sale.order'].sudo().search(
            [('client_order_ref', '=', kw.get('commerce_order', ''))],
            limit=1
        )
        if order and order.state == 'sent':
            order.action_confirm()
            # Generar cupón automáticamente
            if hasattr(order, 'ecocupon_generated') and not order.ecocupon_generated:
                coupon = request.env['ecocupon.coupon'].generate_for_order(order)
                if coupon:
                    order.ecocupon_generated = True
                    order.ecocupon_code = coupon.code
                    _logger.info(f"Flow.cl → Cupón {coupon.code} generado para {order.name}")

        return 'ok'
