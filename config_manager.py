import yaml
import os

def load_config(config_path="config.yaml") -> dict:
    """
    Loads a YAML configuration file.

    :param config_path: Path to the YAML configuration file.
    :return: A dictionary representing the configuration.
    :raises FileNotFoundError: If the config file is not found.
    :raises yaml.YAMLError: If there's an error parsing the YAML file.
    """
    if not os.path.exists(config_path):
        # Try a path relative to this script's location as a fallback
        # (useful if script is called from a different CWD)
        script_dir = os.path.dirname(__file__)
        abs_config_path = os.path.join(script_dir, config_path)
        if os.path.exists(abs_config_path):
            config_path = abs_config_path
        else:
            raise FileNotFoundError(f"Configuration file not found at '{config_path}' or '{abs_config_path}'")

    try:
        with open(config_path, 'r') as stream:
            config = yaml.safe_load(stream)
        return config
    except yaml.YAMLError as exc:
        print(f"Error parsing YAML file: {config_path}")
        # Log the specific parsing error if PyYAML provides details
        if hasattr(exc, 'problem_mark'):
            mark = exc.problem_mark
            print(f"Error position: (Line:{mark.line+1} Column:{mark.column+1})")
        raise # Re-raise the exception after printing details

if __name__ == '__main__':
    try:
        # Attempt to load the default config.yaml from the same directory
        # If run_selector.py is in /app and config.yaml is in /app, this should work.
        # If this script (config_manager.py) is in /app, config_path="config.yaml" is fine.

        # Determine path relative to this script if needed, or assume CWD has config.yaml
        # For testing, let's assume config.yaml is in the current working directory or script's dir
        default_config_file = "config.yaml"
        if not os.path.exists(default_config_file):
             # If not in CWD, try path relative to this script (e.g. if script is in /app, looks for /app/config.yaml)
            script_dir = os.path.dirname(os.path.abspath(__file__)) # Get absolute dir of this script
            default_config_file = os.path.join(script_dir, "config.yaml")
            if not os.path.exists(default_config_file): # If still not found, could be an issue
                 print(f"Warning: config.yaml not found in CWD or script directory '{script_dir}'. Using basic path.")
                 default_config_file = "config.yaml" # Fallback to direct name

        print(f"Attempting to load configuration from: {default_config_file}")
        config_data = load_config(default_config_file)

        print("\nConfiguration loaded successfully:")
        # Pretty print the dictionary
        import json
        print(json.dumps(config_data, indent=4))

        # Example: Accessing a specific value
        # print(f"\nPolygon API Key: {config_data.get('api_keys', {}).get('polygon', 'Not Set')}")
        # print(f"EMA Short Period: {config_data.get('strategy_params', {}).get('ema', {}).get('short_period', 'Not Set')}")

    except FileNotFoundError as fnf_err:
        print(fnf_err)
    except yaml.YAMLError as yml_err:
        print(yml_err)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
