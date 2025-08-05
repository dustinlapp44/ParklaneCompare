import os
import re

def resolve_imports(file_path, project_dir, processed_files):
    """
    Recursively resolve imports and include the code from imported files.
    """
    code = ""
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
        
        code += "".join(lines)
        imports = []

        # Regex to match import statements
        import_pattern = re.compile(r"^(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))")
        
        for line in lines:
            match = import_pattern.match(line)
            if match:
                module = match.group(1) or match.group(2)
                imports.append(module.split(".")[0])  # Get the top-level module name

        for module in imports:
            # Resolve the module to a file path
            module_path = os.path.join(project_dir, module.replace(".", "/") + ".py")
            if os.path.exists(module_path) and module_path not in processed_files:
                processed_files.add(module_path)
                code += f"\n# Imported from {module_path}\n"
                code += resolve_imports(module_path, project_dir, processed_files)
    except Exception as e:
        code += f"\n# Error reading file {file_path}: {e}\n"

    return code


def generate_code_summary_with_imports(output_file="code_summary.txt"):
    """
    Generate a summary of all files in the project, including imported files.
    """
    project_dir = os.getcwd()
    processed_files = set()

    with open(output_file, "w") as summary_file:
        for root, _, files in os.walk(project_dir):
            for file in files:
                if file.endswith(".py"):  # Only process Python files
                    file_path = os.path.join(root, file)
                    if file_path not in processed_files:
                        processed_files.add(file_path)
                        summary_file.write(f"File: {file_path}\n")
                        summary_file.write("-" * 80 + "\n")
                        summary_file.write(resolve_imports(file_path, project_dir, processed_files))
                        summary_file.write("\n" + "=" * 80 + "\n\n")

    print(f"Code summary with imports generated in {output_file}")


# Run the script
generate_code_summary_with_imports()