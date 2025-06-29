import shutil
from pathlib import Path
from users.app_config import AppConfig

app_config = AppConfig("services", "webapp")

def copy_py_files(src: Path, dst: Path):
    for item in src.iterdir():
        if item.is_dir():
            if item.name == "__pycache__":
                continue
            # Create the directory in the destination
            (dst / item.name).mkdir(exist_ok=True)
            copy_py_files(item, dst / item.name)
        elif item.is_file() and item.suffix == ".py":
            shutil.copy2(item, dst / item.name)

def copy_static_folder(deployment_dir: Path):
    static_src = Path("C:\\projects\\the_maze\\simple-hebrew-bot-studio\\dist")
    # Replace the parent dir with deployment_dir
    static_pages = deployment_dir / "users" / "users_programs" / "services" / "webapp" / "static"
    if static_src.exists():
        if static_pages.exists():
            shutil.rmtree(static_pages)
        static_pages.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(static_src, static_pages)
        print(f"Copied static folder to: {static_pages}")
    else:
        print("No static folder found to copy.")

def main():
    root = Path(__file__).parent
    deployment_dir = root / ".." / "deployment"

    # Remove existing deployment dir if exists
    if deployment_dir.exists():
        shutil.rmtree(deployment_dir)
    deployment_dir.mkdir()

    # Copy all .py files and directory structure
    for item in root.iterdir():
        if item.name == "deployment" or item.name == "__pycache__":
            continue
        if item.is_dir():
            if item.name == "__pycache__":
                continue
            (deployment_dir / item.name).mkdir(exist_ok=True)
            copy_py_files(item, deployment_dir / item.name)
        elif item.is_file() and item.suffix == ".py":
            shutil.copy2(item, deployment_dir / item.name)

    print(f"Deployment directory created at: {deployment_dir}")

    # Copy static folder to the correct location inside deployment_dir
    copy_static_folder(deployment_dir)

if __name__ == "__main__":
    main()