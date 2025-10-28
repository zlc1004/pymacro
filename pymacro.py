#!/usr/bin/env python3
"""
PyMacro - A Python script that reads and executes macro files using pyautogui.

Supports the following macro commands:
- var set $<name> <value>: Set a variable (name must start with $)
- var increase $<name> <value>: Increase a variable by a value
- checkpoint "<name>": Create a checkpoint for goto
- goto "<name>": Jump to a checkpoint
- mouse move <x>,<y>: Move mouse to coordinates
- mouse left click: Perform left mouse click
- mouse right click: Perform right mouse click
- mouse left down/up: Press/release left mouse button
- mouse right down/up: Press/release right mouse button
- key down <key>: Press and hold a key
- key up <key>: Release a key
- key press <key>: Press and release a key
- key type "<text>": Type text string
- sleep <ms>: Sleep for specified milliseconds
- if (<condition>): Conditional execution (use $variables in conditions)
- Comments: Lines starting with # are ignored
"""

import pyautogui
import time
import re
import sys
import argparse
from typing import Dict, List, Any, Optional


class MacroParser:
    """Parser for macro files that converts text commands to executable actions."""

    def __init__(self):
        self.variables: Dict[str, int] = {}
        self.checkpoints: Dict[str, int] = {}
        self.commands: List[str] = []
        self.current_line = 0

    def parse_file(self, filename: str) -> List[str]:
        """Parse a macro file and return a list of commands."""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                lines = file.readlines()
        except FileNotFoundError:
            raise FileNotFoundError(f"Macro file '{filename}' not found")

        commands = []
        for i, line in enumerate(lines):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            commands.append(line)

            # Register checkpoints during parsing
            if line.startswith('checkpoint'):
                checkpoint_match = re.match(r'checkpoint\s+"([^"]+)"', line)
                if checkpoint_match:
                    checkpoint_name = checkpoint_match.group(1)
                    self.checkpoints[checkpoint_name] = len(commands) - 1

        self.commands = commands
        return commands

    def parse_coordinates(self, coord_str: str) -> tuple:
        """Parse coordinate string like '100,100' into (x, y) tuple."""
        coords = coord_str.split(',')
        if len(coords) != 2:
            raise ValueError(f"Invalid coordinate format: {coord_str}")
        return int(coords[0].strip()), int(coords[1].strip())

    def evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition string using variable values."""
        # Simple condition evaluation - replace $variables with their values
        for var_name, var_value in self.variables.items():
            condition = condition.replace(f"${var_name}", str(var_value))

        try:
            # Use eval for simple mathematical/comparison expressions
            # Note: In production, this should be replaced with a safer expression evaluator
            return bool(eval(condition))
        except Exception as e:
            print(f"Error evaluating condition '{condition}': {e}")
            return False


class MacroExecutor:
    """Executor that runs parsed macro commands using pyautogui."""

    def __init__(self, parser: MacroParser, simulate: bool = False):
        self.parser = parser
        self.simulate = simulate
        # Configure pyautogui safety settings only if not simulating
        if not simulate:
            pyautogui.FAILSAFE = True  # Move mouse to corner to abort
            pyautogui.PAUSE = 0.1  # Small pause between actions

    def execute_commands(self):
        """Execute all parsed commands."""
        self.parser.current_line = 0

        while self.parser.current_line < len(self.parser.commands):
            command = self.parser.commands[self.parser.current_line]

            try:
                self.execute_command(command)
            except Exception as e:
                print(f"Error executing command '{command}' at line {self.parser.current_line + 1}: {e}")
                break

            self.parser.current_line += 1

    def execute_command(self, command: str):
        """Execute a single macro command."""
        command = command.strip()

        if command.startswith('var set'):
            self._execute_var_set(command)
        elif command.startswith('var increase'):
            self._execute_var_increase(command)
        elif command.startswith('checkpoint'):
            # Checkpoints are handled during parsing, skip during execution
            pass
        elif command.startswith('goto'):
            self._execute_goto(command)
        elif command.startswith('mouse'):
            self._execute_mouse_command(command)
        elif command.startswith('key'):
            self._execute_key_command(command)
        elif command.startswith('sleep'):
            self._execute_sleep(command)
        elif command.startswith('if'):
            self._execute_if(command)
        else:
            print(f"Unknown command: {command}")

    def _execute_var_set(self, command: str):
        """Execute 'var set $<name> <value>' command."""
        match = re.match(r'var\s+set\s+\$(\w+)\s+(\d+)', command)
        if match:
            var_name = match.group(1)
            var_value = int(match.group(2))
            self.parser.variables[var_name] = var_value
            print(f"Set ${var_name} = {var_value}")
        else:
            raise ValueError(f"Invalid var set syntax: {command}")

    def _execute_var_increase(self, command: str):
        """Execute 'var increase $<name> <value>' command."""
        match = re.match(r'var\s+increase\s+\$(\w+)\s+(\d+)', command)
        if match:
            var_name = match.group(1)
            increase_value = int(match.group(2))

            if var_name not in self.parser.variables:
                self.parser.variables[var_name] = 0

            self.parser.variables[var_name] += increase_value
            print(f"Increased ${var_name} by {increase_value}, now = {self.parser.variables[var_name]}")
        else:
            raise ValueError(f"Invalid var increase syntax: {command}")

    def _execute_goto(self, command: str):
        """Execute 'goto "<checkpoint>"' command."""
        match = re.match(r'goto\s+"([^"]+)"', command)
        if match:
            checkpoint_name = match.group(1)
            if checkpoint_name in self.parser.checkpoints:
                self.parser.current_line = self.parser.checkpoints[checkpoint_name]
                print(f"Jumping to checkpoint: {checkpoint_name}")
            else:
                raise ValueError(f"Checkpoint '{checkpoint_name}' not found")
        else:
            raise ValueError(f"Invalid goto syntax: {command}")

    def _execute_mouse_command(self, command: str):
        """Execute mouse-related commands."""
        if command == "mouse left click":
            if not self.simulate:
                pyautogui.click(button='left')
            print("Left mouse click")
        elif command == "mouse right click":
            if not self.simulate:
                pyautogui.click(button='right')
            print("Right mouse click")
        elif command == "mouse left down":
            if not self.simulate:
                pyautogui.mouseDown(button='left')
            print("Left mouse down")
        elif command == "mouse left up":
            if not self.simulate:
                pyautogui.mouseUp(button='left')
            print("Left mouse up")
        elif command == "mouse right down":
            if not self.simulate:
                pyautogui.mouseDown(button='right')
            print("Right mouse down")
        elif command == "mouse right up":
            if not self.simulate:
                pyautogui.mouseUp(button='right')
            print("Right mouse up")
        elif command.startswith("mouse move"):
            # Extract coordinates from "mouse move x,y"
            coord_match = re.match(r'mouse\s+move\s+([\d,\s]+)', command)
            if coord_match:
                x, y = self.parser.parse_coordinates(coord_match.group(1))
                if not self.simulate:
                    pyautogui.moveTo(x, y)
                print(f"Mouse moved to ({x}, {y})")
            else:
                raise ValueError(f"Invalid mouse move syntax: {command}")
        else:
            raise ValueError(f"Unknown mouse command: {command}")

    def _execute_key_command(self, command: str):
        """Execute keyboard-related commands."""
        if command.startswith("key down"):
            # Extract key from "key down <key>"
            key_match = re.match(r'key\s+down\s+(\w+)', command)
            if key_match:
                key = key_match.group(1)
                if not self.simulate:
                    pyautogui.keyDown(key)
                print(f"Key down: {key}")
            else:
                raise ValueError(f"Invalid key down syntax: {command}")
        elif command.startswith("key up"):
            # Extract key from "key up <key>"
            key_match = re.match(r'key\s+up\s+(\w+)', command)
            if key_match:
                key = key_match.group(1)
                if not self.simulate:
                    pyautogui.keyUp(key)
                print(f"Key up: {key}")
            else:
                raise ValueError(f"Invalid key up syntax: {command}")
        elif command.startswith("key press"):
            # Extract key from "key press <key>"
            key_match = re.match(r'key\s+press\s+(\w+)', command)
            if key_match:
                key = key_match.group(1)
                if not self.simulate:
                    pyautogui.press(key)
                print(f"Key press: {key}")
            else:
                raise ValueError(f"Invalid key press syntax: {command}")
        elif command.startswith("key type"):
            # Extract text from "key type "text""
            text_match = re.match(r'key\s+type\s+"([^"]*)"', command)
            if text_match:
                text = text_match.group(1)
                if not self.simulate:
                    pyautogui.typewrite(text)
                print(f"Typed: {text}")
            else:
                raise ValueError(f"Invalid key type syntax: {command}")
        else:
            raise ValueError(f"Unknown key command: {command}")

    def _execute_sleep(self, command: str):
        """Execute 'sleep <ms>' command."""
        match = re.match(r'sleep\s+(\d+)', command)
        if match:
            ms = int(match.group(1))
            seconds = ms / 1000.0
            time.sleep(seconds)
            print(f"Slept for {ms}ms")
        else:
            raise ValueError(f"Invalid sleep syntax: {command}")

    def _execute_if(self, command: str):
        """Execute 'if (<condition>)' command."""
        match = re.match(r'if\s+\(([^)]+)\)', command)
        if match:
            condition = match.group(1)
            if not self.parser.evaluate_condition(condition):
                # Skip the next command if condition is false
                self.parser.current_line += 1
                print(f"Condition '{condition}' is false, skipping next command")
            else:
                print(f"Condition '{condition}' is true, executing next command")
        else:
            raise ValueError(f"Invalid if syntax: {command}")


def main():
    """Main function to run the macro executor."""
    parser = argparse.ArgumentParser(description='Execute macro files using pyautogui')
    parser.add_argument('filename', help='Path to the macro file to execute')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--dry-run', action='store_true', help='Parse commands without executing them')
    parser.add_argument('--simulate', action='store_true', help='Execute logic and show output but skip pyautogui actions')

    args = parser.parse_args()

    try:
        # Create parser and parse the macro file
        macro_parser = MacroParser()
        commands = macro_parser.parse_file(args.filename)

        if args.verbose or args.dry_run:
            print(f"Parsed {len(commands)} commands from {args.filename}")
            for i, cmd in enumerate(commands):
                print(f"  {i+1}: {cmd}")
            print()

        if args.dry_run:
            print("Dry run mode - commands parsed but not executed")
            return

        # Execute the commands
        if args.simulate:
            print(f"Simulating macro file: {args.filename}")
            print("Simulation mode - logic executed but no pyautogui actions performed")
        else:
            print(f"Executing macro file: {args.filename}")
            print("Press Ctrl+C to stop, or move mouse to top-left corner to trigger failsafe")
        print("-" * 50)

        executor = MacroExecutor(macro_parser, simulate=args.simulate)
        executor.execute_commands()

        print("-" * 50)
        print("Macro execution completed")

    except KeyboardInterrupt:
        print("\nMacro execution interrupted by user")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
