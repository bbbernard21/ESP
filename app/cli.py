import click
from flask.cli import with_appcontext
from app import db
from app.test_data import create_test_data
from app.models.user import User

@click.command('create-test-data')
@click.argument('email')
@with_appcontext
def create_test_data_command(email):
    """Create test data for the specified user."""
    user = User.query.filter_by(email=email).first()
    if not user:
        click.echo(f'User with email {email} not found.')
        return
    
    try:
        data = create_test_data(user.id)
        click.echo(f'Created test data for user {user.email}:')
        click.echo(f'- {len(data["courses"])} courses')
        click.echo(f'- 1 semester goal')
        click.echo(f'- {len(data["module_goals"])} module goals')
        click.echo('Test data created successfully!')
    except Exception as e:
        click.echo(f'Error creating test data: {str(e)}')

def init_app(app):
    app.cli.add_command(create_test_data_command) 