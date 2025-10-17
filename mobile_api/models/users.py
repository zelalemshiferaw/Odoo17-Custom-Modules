# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import secrets
import datetime


class ResUsers(models.Model):
    _inherit = "res.users"

    access_token = fields.Char('Access Token', readonly=True, copy=False)
    token_expiry_date = fields.Datetime('Token Expiry Date', readonly=True, copy=False)
    mobile_cart_id = fields.Many2one('mobile.cart', 'Mobile Cart', readonly=True)

    def generate_access_token(self):
        """
        Generate a secure access token for API authentication
        """
        token = secrets.token_urlsafe(32)
        expiry_date = datetime.datetime.now() + datetime.timedelta(hours=24)
        
        self.write({
            'access_token': token,
            'token_expiry_date': expiry_date
        })
        return token

    def verify_access_token(self, token):
        """
        Verify if the access token is valid and not expired
        """
        self.ensure_one()
        if not token or token != self.access_token:
            return False
        
        if not self.token_expiry_date:
            return False
            
        now = datetime.datetime.now()
        if now > self.token_expiry_date:
            return False
            
        return True

    def clear_access_token(self):
        """
        Clear the access token (for logout)
        """
        self.write({
            'access_token': False,
            'token_expiry_date': False
        })

    @api.model
    def authenticate_user(self, db, login, password):
        """
        Authenticate user and return user record if successful
        """
        try:
            # Verify credentials using Odoo's internal authentication
            uid = self.env['res.users'].authenticate(db, login, password, {})
            if uid:
                user = self.env['res.users'].browse(uid)
                token = user.generate_access_token()
                return user, token
            return None, None
        except Exception:
            return None, None