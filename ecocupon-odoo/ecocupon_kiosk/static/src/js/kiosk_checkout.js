/**
 * EcoCupon Kiosk Checkout Widget
 * Shows coupon banner at checkout
 */
odoo.define('ecocupon_kiosk.kiosk_checkout', function(require) {
    "use strict";

    var publicWidget = require('web.public.widget');

    publicWidget.registry.KioskCheckout = publicWidget.Widget.extend({
        selector: '.oe_website_sale',

        start: function() {
            this._super.apply(this, arguments);
            this._showCoupon();
        },

        _showCoupon: function() {
            var self = this;
            this._rpc({
                route: '/ecocupon/emdash_coupon',
                params: {},
            }).then(function(result) {
                if (result && result.coupon_code) {
                    var discountLabel = result.discount_type === 'percentage'
                        ? result.discount + '%'
                        : '$' + result.discount;

                    var banner = $(
                        '<div class="ecocupon-banner">' +
                            '<h4>🎉 ¡Gracias por tu compra!</h4>' +
                            '<p>Tu cupón para la próxima orden:</p>' +
                            '<div class="ecocupon-code">' + result.coupon_code + '</div>' +
                            '<p>Descuento: <strong>' + discountLabel + '</strong></p>' +
                            '<p style="font-size:0.85em;color:#92400e;">Válido 30 días</p>' +
                        '</div>'
                    );

                    // Insert at top of checkout
                    var target = $('.o_checkout_summary, .oe_website_sale .container');
                    if (target.length) {
                        target.first().before(banner);
                    } else {
                        $('main').prepend(banner);
                    }
                }
            }).catch(function() {
                // Silent fail — coupon is nice-to-have
            });
        },
    });

    return publicWidget.registry.KioskCheckout;
});
