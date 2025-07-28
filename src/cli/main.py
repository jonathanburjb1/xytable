#!/usr/bin/env python3
"""
X-Y Table Control System CLI

Main entry point for the command-line interface.
"""

import click
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import ConfigManager
from src.utils.logging import setup_logging
from src.cli.commands import MovementCommands, MesaTestCommands


@click.group()
@click.option('--config', '-c', 
              default='config/settings.yaml',
              help='Configuration file path')
@click.option('--verbose', '-v', 
              is_flag=True, 
              help='Enable verbose logging')
@click.pass_context
def cli(ctx, config, verbose):
    """
    X-Y Table Control System
    
    Control your X-Y table with precise step-based movements.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Load configuration
    try:
        config_manager = ConfigManager(config)
        ctx.obj['config'] = config_manager
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)
    
    # Setup logging
    log_level = 'DEBUG' if verbose else config_manager.get('logging.level', 'INFO')
    setup_logging(log_level, config_manager.get('logging.file', 'logs/xytable.log'))
    
    # Initialize command objects
    ctx.obj['movement'] = MovementCommands(config_manager)

    ctx.obj['mesa_test'] = MesaTestCommands(config_manager)


@cli.group()
@click.pass_context
def move(ctx):
    """
    Move one or both axes by a specified distance (in inches).
    """
    pass


@move.command(context_settings=dict(allow_interspersed_args=False))
@click.option('--speed', '-s', 
              type=float, 
              help='Movement speed in inches per second')
@click.argument('distance', type=float)
@click.pass_context
def x(ctx, speed, distance):
    """
    Move X axis by specified distance in inches.
    
    DISTANCE: Distance to move in inches (positive = forward, negative = backward)
    """
    try:
        ctx.obj['movement'].move_x(distance, speed)
        click.echo(f"X axis moved by {distance} inches")
    except Exception as e:
        click.echo(f"Error moving X axis: {e}", err=True)
        sys.exit(1)


@move.command(context_settings=dict(allow_interspersed_args=False))
@click.option('--speed', '-s', 
              type=float, 
              help='Movement speed in inches per second')
@click.argument('distance', type=float)
@click.pass_context
def y(ctx, speed, distance):
    """
    Move Y axis by specified distance in inches.
    
    DISTANCE: Distance to move in inches (positive = forward, negative = backward)
    """
    try:
        ctx.obj['movement'].move_y(distance, speed)
        click.echo(f"Y axis moved by {distance} inches")
    except Exception as e:
        click.echo(f"Error moving Y axis: {e}", err=True)
        sys.exit(1)


@move.command(context_settings=dict(allow_interspersed_args=False))
@click.option('--speed', '-s', 
              type=float, 
              help='Movement speed in inches per second')
@click.argument('x_distance', type=float)
@click.argument('y_distance', type=float)
@click.pass_context
def xy(ctx, speed, x_distance, y_distance):
    """
    Move both X and Y axes simultaneously.
    
    X_DISTANCE: Distance to move X axis (inches)
    Y_DISTANCE: Distance to move Y axis (inches)
    """
    try:
        ctx.obj['movement'].move_xy(x_distance, y_distance, speed)
        click.echo(f"X axis moved by {x_distance} inches, Y axis moved by {y_distance} inches")
    except Exception as e:
        click.echo(f"Error moving axes: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--x', 'x_pos', type=float, required=True, help='Absolute X position in inches')
@click.option('--y', 'y_pos', type=float, required=True, help='Absolute Y position in inches')
@click.pass_context
def move_absolute(ctx, x_pos, y_pos):
    """
    Move to an absolute X/Y position in inches using Mesa MDI G0.
    """
    try:
        ctx.obj['movement'].move_absolute(x=x_pos, y=y_pos)
        click.echo(f"Moved to absolute position X={x_pos}, Y={y_pos} inches")
    except Exception as e:
        click.echo(f"Error during absolute move: {e}", err=True)
        sys.exit(1)





@cli.command()
@click.pass_context
def home(ctx):
    """
    Home both axes to their reference positions.
    """
    try:
        ctx.obj['movement'].home_all()
        click.echo("Both axes homed successfully")
    except Exception as e:
        click.echo(f"Error during homing: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('axis', type=click.Choice(['x', 'y']))
@click.pass_context
def home_axis(ctx, axis):
    """
    Home a specific axis to its reference position.
    
    AXIS: Axis to home ('x' or 'y')
    """
    try:
        ctx.obj['movement'].home_axis(axis)
        click.echo(f"{axis.upper()} axis homing command sent successfully")
    except Exception as e:
        click.echo(f"Error during {axis} axis homing: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def stop(ctx):
    """
    Emergency stop - halt all movement immediately.
    """
    try:
        ctx.obj['movement'].emergency_stop()
        click.echo("Emergency stop activated - all movement halted")
    except Exception as e:
        click.echo(f"Error during emergency stop: {e}", err=True)
        sys.exit(1)


@cli.group()
@click.pass_context
def mesa(ctx):
    """
    Mesa board testing and debugging commands.
    """
    pass


@mesa.command()
@click.pass_context
def test_connection(ctx):
    """
    Test connection to the Mesa board.
    """
    try:
        result = ctx.obj['mesa_test'].test_connection()
        click.echo("Mesa Connection Test:")
        click.echo(f"  Success: {result['success']}")
        click.echo(f"  Connected: {result['connected']}")
        click.echo(f"  Message: {result['message']}")
        if 'error' in result:
            click.echo(f"  Error: {result['error']}")
        if 'status_response' in result:
            click.echo(f"  Status Response: {result['status_response']}")
    except Exception as e:
        click.echo(f"Error testing Mesa connection: {e}", err=True)
        sys.exit(1)


@mesa.command()
@click.argument('axis', type=click.Choice(['x', 'y']))
@click.pass_context
def test_axis(ctx, axis):
    """
    Test axis enable/disable functionality.
    
    AXIS: 'x' or 'y'
    """
    try:
        result = ctx.obj['mesa_test'].test_axis_control(axis)
        click.echo(f"Mesa {axis.upper()} Axis Test:")
        click.echo(f"  Success: {result['success']}")
        click.echo(f"  Enable Result: {result.get('enable_result', 'N/A')}")
        click.echo(f"  Disable Result: {result.get('disable_result', 'N/A')}")
        click.echo(f"  Message: {result['message']}")
        if 'error' in result:
            click.echo(f"  Error: {result['error']}")
    except Exception as e:
        click.echo(f"Error testing {axis} axis: {e}", err=True)
        sys.exit(1)


@mesa.command()
@click.argument('axis', type=click.Choice(['x', 'y']))
@click.argument('steps', type=int)
@click.argument('speed', type=int)
@click.pass_context
def test_move(ctx, axis, steps, speed):
    """
    Test movement command functionality.
    
    AXIS: 'x' or 'y'
    STEPS: Number of steps to move
    SPEED: Movement speed in steps per second
    """
    try:
        result = ctx.obj['mesa_test'].test_movement(axis, steps, speed)
        click.echo(f"Mesa {axis.upper()} Movement Test:")
        click.echo(f"  Success: {result['success']}")
        click.echo(f"  Message: {result['message']}")
        if 'error' in result:
            click.echo(f"  Error: {result['error']}")
    except Exception as e:
        click.echo(f"Error testing {axis} movement: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--channel', type=click.Choice(['0', '1']), required=True, help='IO channel: 1 for flood, 0 for mist')
@click.option('--state', type=click.Choice(['on', 'off']), required=True, help='State: on or off')
@click.pass_context
def set_io(ctx, channel, state):
    """
    Set the state of the flood (1) or mist (0) output.
    """
    io_channel = int(channel)
    state_bool = state.lower() == 'on'
    try:
        ctx.obj['movement'].set_io(io_channel, state_bool)
        click.echo(f"Set IO channel {io_channel} ({'flood' if io_channel == 1 else 'mist'}) to {'ON' if state_bool else 'OFF'}")
    except Exception as e:
        click.echo(f"Error setting IO: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
