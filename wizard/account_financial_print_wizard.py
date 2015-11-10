# -*- coding: utf-8 -*-
# author: cysnake4713
#

from openerp import tools
from openerp import models, fields, api
from openerp.tools.translate import _


class AccountingReportInheirt(models.TransientModel):
    _inherit = 'accounting.report'

    @api.cr_uid_ids_context
    def _print_report(self, cr, uid, ids, data, context=None):
        data['form'].update(self.read(cr, uid, ids,
                                      ['date_from_cmp', 'debit_credit', 'date_to_cmp', 'fiscalyear_id_cmp', 'period_from_cmp', 'period_to_cmp',
                                       'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter', 'target_move'], context=context)[0])
        if 'oecn_print' in context:
            data['oecn_print'] = context['oecn_print']
            if context['oecn_print'] == 'pal':
                return self.pool['report'].get_action(cr, uid, [], 'oecn_account_print.report_oe_cn_pal_financial', data=data, context=context)
            if context['oecn_print'] == 'aab':
                return self.pool['report'].get_action(cr, uid, [], 'oecn_account_print.report_oe_cn_aab_financial', data=data, context=context)
        return self.pool['report'].get_action(cr, uid, [], 'account.report_financial', data=data, context=context)
