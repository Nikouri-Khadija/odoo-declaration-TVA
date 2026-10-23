# ---------------------------------------------------------------------------
# Utilitaires paiement — partagés entre account_move et le wizard
# ---------------------------------------------------------------------------

from .constants import PAYMENT_MODE_CODES, PAYMENT_MODE_DEFAULT


def payment_to_mp_code(payment):

    journal_type = payment.journal_id.type
    method_code = (
        payment.payment_method_line_id.payment_method_id.code or ''
    ).lower()

    if journal_type == 'cash':
        return '1'

    if journal_type == 'bank':
        if method_code == 'check_printing':
            return '2'   # Chèque
        if method_code == 'direct_debit':
            return '3'   # Prélèvement
        if method_code == 'manual':
            return '4'   # Virement
        return '7'       

    return PAYMENT_MODE_DEFAULT


def get_payment_info(move):
    """
    Retourne (date_paiement, code_EDI) pour une facture.
    """
    payments = move.reconciled_payment_ids or move.matched_payment_ids
    if not payments:
        return False, PAYMENT_MODE_DEFAULT

    payment = payments[0]
    return payment.date, payment_to_mp_code(payment)