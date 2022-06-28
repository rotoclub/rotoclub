# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models, tools, _

DICT_LANG = {
    'AR': 'es_AR',
    'BO': 'es_BO',
    'ES': 'es_ES',
    'CL': 'es_ES',
    'BE': 'fr_BE',
    'AU': 'en_AU',
    'BG': 'bg_BG',
    'BR': 'pt_BR',
    'CA': 'en_CA',
    'CN': 'zh_HK',
    'CO': 'es_CO',
    'CR': 'es_CR',
    'CU': 'es_ES',
    'CZ': 'cs_CZ',
    'DE': 'de_DE',
    'DK': 'da_DK',
    'DO': 'es_ES',
    'EC': 'es_EC',
    'EE': 'et_EE',
    'EG': 'ar_SY',
    'EH': 'ar_SY',
    'FR': 'fr_FR',
    'GF': 'fr_CH',
    'GR': 'el_GR',
    'GT': 'es_GT',
    'HK': 'zh_HK',
    'HN': 'es_ES',
    'HR': 'hr_HR',
    'HU': 'hu_HU',
    'ID': 'id_ID',
    'IN': 'hi_IN',
    'IT': 'it_IT',
    'JP': 'ja_JP',
    'KP': 'ko_KP',
    'KR': 'ko_KR',
    'LA': 'lo_LA',
    'LT': 'lt_LT',
    'LU': 'lb_LU',
    'LV': 'lv_LV',
    'MF': 'fr_FR',
    'MN': 'mn_MN',
    'MX': 'es_MX',
    'NO': 'nb_NO',
    'PA': 'es_PA',
    'PE': 'es_PE',
    'PF': 'fr_CH',
    'PM': 'fr_CH',
    'PL': 'pl_PL',
    'PN': 'fr_CH',
    'PT': 'pt_PT',
    'PY': 'es_PY',
    'QA': 'ar_001',
    'RE': 'fr_FR',
    'RO': 'ro_RO',
    'RS': 'sr_RS',
    'RU': 'ru_RU',
    'SA': 'ar_001',
    'SE': 'sv_SE',
    'SI': 'sl_SI',
    'SK': 'sk_SK',
    'TH': 'th_TH',
    'TR': 'tr_TR',
    'GB': 'en_GB',
    'UY': 'es_UY',
    'UY': 'es_UY',
    'VE': 'es_VE',
    'VN': 'vi_VN',
}


class Partner(models.Model):
    _inherit = "res.partner"

    @api.constrains('country_id')
    def _constrain_language(self):
        for record in self:
            if record.country_id:
                lang_value = 'en_US'
                country = record.country_id
                keys_list = DICT_LANG.keys()
                if country.code in keys_list:
                    for key in keys_list:
                        if key == country.code:
                            lang_value = DICT_LANG.get(key)
                obj_lang_inactive_ids = self.env['res.lang'].search([('code', '=', lang_value), ('active', '=', False)])
                if obj_lang_inactive_ids:
                    lang_change = obj_lang_inactive_ids[0]
                    lang = self.env['base.language.install'].create({'lang': lang_change.code, 'overwrite': True})
                    lang.lang_install()
                    lang_value = lang.lang
                obj_lang_active_ids = self.env['res.lang'].search([('code', '=', lang_value), ('active', '=', True)])
                if obj_lang_active_ids:
                    lang_value = obj_lang_active_ids[0]
                if lang_value:
                    record.lang = lang_value.code
                    record.message_post(body=_("Lang: %s") % lang_value.name)
