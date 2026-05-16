import json
import sys
from engine import ActionEngine


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'actions.json'

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Config not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON error: {e}")
        sys.exit(1)

    engine = ActionEngine(config)
    actions = config.get('actions', [])
    
    # 应用全局配置
    if config.get('keep_template'):
        engine.keep_template = True
    if config.get('templates_dir'):
        engine.templates_dir = config['templates_dir']

    if isinstance(actions, dict):
        actions = [actions]

    print(f"Loaded {len(actions)} actions from {config_path}")

    try:
        for action in actions:
            engine.execute(action)
    except KeyboardInterrupt:
        print("\nInterrupted")

    print("Done")


if __name__ == '__main__':
    main()
