import yaml
from genson import SchemaBuilder
from jsonschema import validate, ValidationError
import json

def load_yaml(yaml_path):
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def generate_schema(data):
    builder = SchemaBuilder()
    builder.add_object(data)
    return builder.to_schema()

def validate_yaml(data, schema):
    try:
        validate(instance=data, schema=schema)
        print("✅ YAML is valid against the schema.")
    except ValidationError as e:
        print("❌ YAML validation error:")
        print(e)

if __name__ == '__main__':
    yaml_file = 'config/data.yml'  # replace with your file
    data = load_yaml(yaml_file)
    schema = generate_schema(data)

    print("🔧 Generated schema:")
    print(json.dumps(schema, indent=2))

    print("\n🔍 Validating YAML against the schema...")
    validate_yaml(data, schema)
