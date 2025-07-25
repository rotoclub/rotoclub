# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tip_move_id = fields.Many2one(
        string='Tip Move',
        comodel_name='account.move'
    )
    has_error = fields.Boolean(
        string='Has Error'
    )
    sale_api_line_id = fields.Many2one(
        comodel_name='sale.api.line',
        string='Sale Api Line',
        ondelete='restrict',
        tracking=1
    )

    def action_tips_moves(self):
        """ Redirect the user move related with Tips.
        :return:    An action on account.move.
        """
        self.ensure_one()

        action = {
            'name': _("Tips Move"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        action.update({
            'view_mode': 'form',
            'res_id': self.tip_move_id.id,
        })
        return action

    def generate_tip_account(self):
        """
        Function to create a move account, to compute the tips Amount.
        The tips amount should not be considered with the Invoice directly. That's why is done directly the move.
        """
        # search the journal for sales
        journal_id = self.env['account.mapping'].search([('company_id', '=', self.company_id.id)], limit=1).tip_journal_id
        accounts = self.env['tips.config'].search([('company_id', '=', self.company_id.id),
                                                   ('sale_center_id', '=', self.sale_center_id.id)], limit=1)
        if not journal_id or not accounts:
            raise ValidationError(_("Verify the Journal and Account mapped for tips related with %s") % self.sale_center_id.name)
        lines_type = ['debit', 'credit']
        # prepare the value dictionary to create the movement
        vals = {
            'ref': self.client_order_ref or '',
            'move_type': 'entry',
            'invoice_origin': self.name,
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'line_ids': [],
        }
        if journal_id:
            vals.update({'journal_id': journal_id.id})
        # add the invoice lines according to the order line list
        for value in lines_type:
            debit = 0.0
            credit = 0.0
            if value == 'debit':
                debit = self.tips_amount
                account_id = accounts.counterpart_account_id.id
            else:
                credit = self.tips_amount
                account_id = accounts.account_id.id
            vals['line_ids'].append((0, 0,
                                     {'analytic_account_id': self.sale_center_id.analytic_id.id if self.sale_center_id else False,
                                      'partner_id': self.partner_id.id,
                                      'name': 'Tip({})'.format(self.name),
                                      'company_id': self.company_id.id,
                                      'account_id': account_id,
                                      'debit': debit,
                                      'credit': credit,
                                      }))
        # create move
        invoice_obj = self.env['account.move'].create(vals)
        # validate the new move
        invoice_obj.action_post()
        self.tip_move_id = invoice_obj

    # @staticmethod
    # def complete_sequence(number):
    #     length = 6
    #     return str(number).zfill(length)

    def update_custom_mapping_accounts(self, invoice):
        """"
        Function to get the rigth journal in case its mapped in configuration.
        Mapped is get it from Agora/Settings/Accounting config/Sale Center-Accounts
        @Return the Accounts related with the Sale Center coming from Agora ticket
        """
        center_account = self.env['sale.center.account'].search([('sale_center_id', '=', invoice.sale_center_id.id)], limit=1)
        if center_account:
            counterpart = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.internal_group == 'asset')
            invoice_lines = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.internal_group == 'income')
            invoice_lines.account_id = center_account.account_id
            counterpart.account_id = center_account.counterpart_account_id
        else:
            raise ValidationError(_("Please verify the Sale Centers list it's updated"))

    def _create_invoices(self, grouped=False, final=False, date=None):
        res = super(SaleOrder, self)._create_invoices(grouped=False, final=False, date=None)
        for rec in self:
            # TODO almacenar en la sale.order el tipo de factura para poder buscar el diario desde aquí y actualizarlo
            # TODO de esta forma se podría quitar el código que actualiza estos campos en la función generate_invoice
            # TODO por eso he comentado el update del campo 'name'
            # name = '{}/{}'.format(rec.serie, self.complete_sequence(rec.number))
            res.sale_center_id = rec.sale_center_id
            res.invoice_line_ids.analytic_account_id = rec.sale_center_id.analytic_id.id
            res.invoice_date = rec.date_order.date()
            self.update_custom_mapping_accounts(res)
            res.update({
                'invoice_date_due': res.invoice_date,
                'date': res.invoice_date,
                'number': rec.number,
                'serie': rec.serie,
                # 'name': name,
                'business_date': rec.business_date,
                'work_place_id': rec.work_place_id.id
            })
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_addins = fields.Boolean(
        string='Is Addins'
    )
    is_invitation = fields.Boolean(
        string='Invitation'
    )
    index = fields.Integer(
        string='Index',
        help='Number of the line coming from Agora to be identify'
    )
    agora_loss_id = fields.Integer(
        string='Agora Loss'
    )
