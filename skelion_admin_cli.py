import os
import json
import click
import requests

API_BASE = os.getenv('ADMIN_API_BASE', 'http://localhost:8000')
TOKEN = os.getenv('ADMIN_API_TOKEN')

def _auth_headers():
    headers = {}
    if TOKEN:
        headers['Authorization'] = f'Bearer {TOKEN}'
    return headers

def _post(endpoint: str, payload: dict):
    url = f"{API_BASE}{endpoint}"
    response = requests.post(url, json=payload, headers=_auth_headers())
    response.raise_for_status()
    return response.json()

def _prompt_common():
    reason = click.prompt('Reason', type=str)
    factor = click.prompt('Second‑factor code', hide_input=True, confirmation_prompt=False)
    return reason, factor

def _handle_dry_run(payload: dict):
    click.echo(json.dumps(payload, indent=2))
    raise SystemExit(0)

@click.group()
def cli():
    """Skelion admin CLI"""
    pass

@cli.command(name='grant-credits')
@click.option('--user-id', required=True, type=int, help='User ID to grant credits to')
@click.option('--amount', required=True, type=int, help='Amount of credits')
@click.option('--dry-run', is_flag=True, default=False, help='Print request payload without sending')
def grant_credits(user_id: int, amount: int, dry_run: bool):
    """Grant credits to a user"""
    reason, factor = _prompt_common()
    payload = {
        'user_id': user_id,
        'amount': amount,
        'reason': reason,
        'second_factor': factor,
    }
    if dry_run:
        _handle_dry_run(payload)
    result = _post('/credits/grant', payload)
    click.echo(json.dumps(result))

@cli.command(name='adjust-credits')
@click.option('--user-id', required=True, type=int, help='User ID')
@click.option('--delta', required=True, type=int, help='Credit delta (positive or negative)')
@click.option('--dry-run', is_flag=True, default=False, help='Print request payload without sending')
def adjust_credits(user_id: int, delta: int, dry_run: bool):
    """Adjust credits for a user"""
    reason, factor = _prompt_common()
    payload = {
        'user_id': user_id,
        'delta': delta,
        'reason': reason,
        'second_factor': factor,
    }
    if dry_run:
        _handle_dry_run(payload)
    result = _post('/credits/adjust', payload)
    click.echo(json.dumps(result))

@cli.command(name='change-tier')
@click.option('--org-id', required=True, type=int, help='Organization ID')
@click.option('--tier', required=True, type=str, help='Target tier')
@click.option('--dry-run', is_flag=True, default=False, help='Print request payload without sending')
def change_tier(org_id: int, tier: str, dry_run: bool):
    """Change subscription tier for an organization"""
    reason, factor = _prompt_common()
    payload = {
        'org_id': org_id,
        'tier': tier,
        'reason': reason,
        'second_factor': factor,
    }
    if dry_run:
        _handle_dry_run(payload)
    result = _post('/tier/change', payload)
    click.echo(json.dumps(result))

@cli.command(name='reconcile-order')
@click.option('--order-id', required=True, type=int, help='Order ID')
@click.option('--dry-run', is_flag=True, default=False, help='Print request payload without sending')
def reconcile_order(order_id: int, dry_run: bool):
    """Reconcile a paid order"""
    reason, factor = _prompt_common()
    payload = {
        'order_id': order_id,
        'reason': reason,
        'second_factor': factor,
    }
    if dry_run:
        _handle_dry_run(payload)
    result = _post('/order/reconcile', payload)
    click.echo(json.dumps(result))

@cli.command(name='refund-payment')
@click.option('--payment-id', required=True, type=int, help='Payment ID to refund')
@click.option('--dry-run', is_flag=True, default=False, help='Print request payload without sending')
def refund_payment(payment_id: int, dry_run: bool):
    """Refund a payment"""
    reason, factor = _prompt_common()
    payload = {
        'payment_id': payment_id,
        'reason': reason,
        'second_factor': factor,
    }
    if dry_run:
        _handle_dry_run(payload)
    result = _post('/payment/refund', payload)
    click.echo(json.dumps(result))

@cli.command(name='toggle-kill-switch')
@click.option('--enable', is_flag=True, default=False, help='Enable kill switch')
@click.option('--disable', is_flag=True, default=False, help='Disable kill switch')
@click.option('--dry-run', is_flag=True, default=False, help='Print request payload without sending')
def toggle_kill_switch(enable: bool, disable: bool, dry_run: bool):
    """Toggle global kill switch"""
    if enable == disable:
        raise click.UsageError('Specify either --enable or --disable')
    action = 'enable' if enable else 'disable'
    reason, factor = _prompt_common()
    payload = {
        'action': action,
        'reason': reason,
        'second_factor': factor,
    }
    if dry_run:
        _handle_dry_run(payload)
    result = _post('/kill-switch/toggle', payload)
    click.echo(json.dumps(result))

if __name__ == '__main__':
    cli()
