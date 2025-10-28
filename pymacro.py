#!/usr/bin/env python3
"""
PyMacro - A Python script that reads and executes macro files using pyautogui.

Supports the following macro commands:
- var set $<name> <value>: Set a variable to integer value (name must start with $)
- var set $<name> (x,y): Set a variable to position coordinates
- var increase $<name> <value>: Increase a variable by a value
- checkpoint "<name>": Create a checkpoint for goto
- goto "<name>": Jump to a checkpoint
- mouse move <x>,<y>: Move mouse to coordinates
- mouse move $<pos>: Move mouse to position stored in variable
- mouse left click: Perform left mouse click
- mouse right click: Perform right mouse click
- mouse left down/up: Press/release left mouse button
- mouse right down/up: Press/release right mouse button
- key down <key>: Press and hold a key
- key up <key>: Release a key
- key press <key>: Press and release a key
- key type "<text>": Type text string
- sleep <ms>: Sleep for specified milliseconds
- if (<condition>): Conditional execution (use $variables in conditions, $ for last command status)
- cv match <image.png> <threshold>% $<pos>: Find template image on screen and store center position
- end: Terminate macro execution
- Comments: Lines starting with # are ignored
"""

import pyautogui
import time
import re
import sys
import argparse
import cv2
import numpy as np
from screeninfo import get_monitors
from typing import Dict, List, Any, Optional, Union, Tuple


class MacroParser:
    """Parser for macro files that converts text commands to executable actions."""

    def __init__(self):
        self.variables: Dict[str, Union[int, Tuple[int, int]]] = {}
        self.checkpoints: Dict[str, int] = {}
        self.commands: List[str] = []
        self.current_line = 0
        self.last_command_status = 0  # 0 for success, 1 for failure

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

    def find_template(self, image: np.ndarray, template: np.ndarray, threshold: float) -> Tuple[Optional[Tuple[int, int]], np.ndarray]:
        """Find template in image using OpenCV template matching."""
        # Convert both images to grayscale for better matching
        if len(image.shape) == 3:
            image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            image_gray = image

        if len(template.shape) == 3:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template

        h, w = template_gray.shape
        image2 = image.copy()

        # Perform template matching
        res = cv2.matchTemplate(image_gray, template_gray, cv2.TM_CCOEFF_NORMED)

        # Find the best match location
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        print(f"Template matching result - Max confidence: {max_val:.3f}, Required: {threshold:.3f}")

        if max_val >= threshold:
            # Use the best match location
            top_left = max_loc
            bottom_right = (top_left[0] + w, top_left[1] + h)

            # Draw rectangle on result image for debugging
            cv2.rectangle(image2, top_left, bottom_right, (0, 0, 255), 2)

            # Calculate center position
            center_x = top_left[0] + w // 2
            center_y = top_left[1] + h // 2

            print(f"Match found at top-left: {top_left}, center: ({center_x}, {center_y})")

            return (center_x, center_y), image2

        return None, image2

    def evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition string using variable values."""
        # Replace special $ variable (last command status)
        condition = condition.replace("$", str(self.last_command_status))

        # Simple condition evaluation - replace $variables with their values
        for var_name, var_value in self.variables.items():
            if isinstance(var_value, tuple):
                # For position variables, we might need special handling in conditions
                condition = condition.replace(f"${var_name}", f"({var_value[0]}, {var_value[1]})")
            else:
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
        elif command.startswith('cv match'):
            self._execute_cv_match(command)
        elif command == 'end':
            self._execute_end(command)
        else:
            print(f"Unknown command: {command}")

    def _execute_var_set(self, command: str):
        """Execute 'var set $<name> <value>' command."""
        # Check for position syntax: var set $pos (x,y)
        pos_match = re.match(r'var\s+set\s+\$(\w+)\s+\((\d+),(\d+)\)', command)
        if pos_match:
            var_name = pos_match.group(1)
            x = int(pos_match.group(2))
            y = int(pos_match.group(3))
            self.parser.variables[var_name] = (x, y)
            print(f"Set ${var_name} = ({x}, {y})")
            return

        # Check for integer syntax: var set $name value
        int_match = re.match(r'var\s+set\s+\$(\w+)\s+(\d+)', command)
        if int_match:
            var_name = int_match.group(1)
            var_value = int(int_match.group(2))
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
        if command == "mouse left click" or command == "mouse click left":
            if not self.simulate:
                pyautogui.click(button='left')
            print("Left mouse click")
        elif command == "mouse right click" or command == "mouse click right":
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
            # Check for variable syntax: mouse move $pos
            var_match = re.match(r'mouse\s+move\s+\$(\w+)', command)
            if var_match:
                var_name = var_match.group(1)
                if var_name in self.parser.variables:
                    var_value = self.parser.variables[var_name]
                    if isinstance(var_value, tuple):
                        x, y = var_value
                        if not self.simulate:
                            pyautogui.moveTo(x, y)
                        print(f"Mouse moved to ${var_name} ({x}, {y})")
                    else:
                        raise ValueError(f"Variable ${var_name} is not a position")
                else:
                    raise ValueError(f"Variable ${var_name} not found")
                return

            # Check for coordinate syntax: mouse move (x,y) or mouse move x,y
            coord_match = re.match(r'mouse\s+move\s+\(?([^\)]+)\)?', command)
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
                # Skip all commands until we find the corresponding "end"
                self._skip_to_end()
                print(f"Condition '{condition}' is false, skipping to end")
            else:
                print(f"Condition '{condition}' is true, executing conditional block")
        else:
            raise ValueError(f"Invalid if syntax: {command}")

    def _skip_to_end(self):
        """Skip commands until we find an 'end' command."""
        while self.parser.current_line < len(self.parser.commands) - 1:
            self.parser.current_line += 1
            if self.parser.commands[self.parser.current_line].strip() == 'end':
                break

    def _execute_cv_match(self, command: str):
        """Execute 'cv match image.png 50% $pos' command."""
        match = re.match(r'cv\s+match\s+([^\s]+)\s+(\d+)%\s+\$(\w+)', command)
        if match:
            image_path = match.group(1)
            threshold_percent = int(match.group(2))
            var_name = match.group(3)

            threshold = threshold_percent / 100.0

            try:
                # Load template image
                template = cv2.imread(image_path, cv2.IMREAD_COLOR)
                if template is None:
                    raise FileNotFoundError(f"Template image '{image_path}' not found or could not be loaded")

                print(f"Loaded template '{image_path}' with shape: {template.shape}")

                if not self.simulate:
                    # Take screenshot and convert to OpenCV format
                    screenshot = pyautogui.screenshot()
                    # Convert PIL image to numpy array, then RGB to BGR for OpenCV
                    screenshot_np = np.array(screenshot)
                    img_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

                    # Get screen size for DPI scaling calculation
                    screen_width, screen_height = pyautogui.size()
                    screenshot_width, screenshot_height = screenshot.size

                    # Calculate DPI scaling factors
                    scale_x = screenshot_width / screen_width
                    scale_y = screenshot_height / screen_height

                    print(f"Screenshot: {screenshot_width}x{screenshot_height}, Screen: {screen_width}x{screen_height}")
                    print(f"DPI scaling factors: X={scale_x:.2f}, Y={scale_y:.2f}")
                    print(f"Template matching with threshold: {threshold} ({threshold_percent}%)")

                    # Find template in screenshot
                    center_pos, result_img = self.parser.find_template(img_bgr, template, threshold)

                    if center_pos:
                        # Adjust position for DPI scaling
                        adjusted_x = int(center_pos[0] / scale_x)
                        adjusted_y = int(center_pos[1] / scale_y)
                        adjusted_pos = (adjusted_x, adjusted_y)

                        # Success: set position variable and status to 0
                        self.parser.variables[var_name] = adjusted_pos
                        self.parser.last_command_status = 0
                        print(f"✓ Template '{image_path}' found at screenshot position {center_pos}")
                        print(f"✓ Adjusted for DPI scaling to logical position {adjusted_pos}, stored in ${var_name}")
                    else:
                        # Failure: set status to 0
                        self.parser.last_command_status = 0
                        print(f"✗ Template '{image_path}' not found (threshold: {threshold_percent}%)")
                else:
                    # Simulation mode
                    print(f"[SIMULATE] cv match '{image_path}' {threshold_percent}% -> ${var_name}")
                    # In simulation, assume success and set dummy position
                    self.parser.variables[var_name] = (500, 300)
                    self.parser.last_command_status = 0

            except Exception as e:
                print(f"Error in cv match: {e}")
                self.parser.last_command_status = 0
        else:
            raise ValueError(f"Invalid cv match syntax: {command}")

    def _execute_end(self, command: str):
        """Execute 'end' command to mark end of conditional block."""
        print("End of conditional block")
        # Just continue execution - end marks the end of an if block


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
