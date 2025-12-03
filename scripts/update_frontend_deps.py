#!/usr/bin/env python3
"""
Frontend Dependencies Updater

This script downloads and updates Bootstrap, Bootstrap Icons, and Chart.js
from CDN URLs to their latest versions, including all necessary files
(CSS, JS, fonts, maps).
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import json


# Constants
VENDOR_DIR = Path("app/static/vendor")
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Library configurations with CDN URLs
LIBRARIES: Dict[str, Dict[str, str]] = {
    "bootstrap": {
        "package": "bootstrap",
        "cdn_base": "https://cdn.jsdelivr.net/npm/bootstrap@{version}/dist/",
        "files": [
            ("css/bootstrap.min.css", "css/bootstrap.min.css"),
            ("css/bootstrap.min.css.map", "css/bootstrap.min.css.map"),
            ("js/bootstrap.bundle.min.js", "js/bootstrap.bundle.min.js"),
            ("js/bootstrap.bundle.min.js.map", "js/bootstrap.bundle.min.js.map"),
        ],
    },
    "bootstrap-icons": {
        "package": "bootstrap-icons",
        "cdn_base": "https://cdn.jsdelivr.net/npm/bootstrap-icons@{version}/",
        "files": [
            ("font/bootstrap-icons.min.css", "bootstrap-icons.min.css"),
            ("font/fonts/bootstrap-icons.woff", "fonts/bootstrap-icons.woff"),
            ("font/fonts/bootstrap-icons.woff2", "fonts/bootstrap-icons.woff2"),
        ],
    },
    "chartjs": {
        "package": "chart.js",
        "cdn_base": "https://cdn.jsdelivr.net/npm/chart.js@{version}/dist/",
        "files": [
            ("chart.umd.min.js", "chart.umd.min.js"),
            ("chart.umd.js.map", "chart.umd.js.map"),
        ],
    },
}


class FrontendUpdater:
    """Handles updating frontend dependencies from CDN."""

    def __init__(self, vendor_dir: Optional[Path] = None) -> None:
        """Initialize the updater.

        Args:
            vendor_dir: Path to the vendor directory. Defaults to app/static/vendor.
        """
        self.vendor_dir = vendor_dir or VENDOR_DIR
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("frontend_update.log"),
            ],
        )
        return logging.getLogger(__name__)

    def _get_latest_version(self, package_name: str) -> str:
        """Get the latest version of a package from jsdelivr CDN API.

        Args:
            package_name: Name of the npm package

        Returns:
            Latest version string

        Raises:
            RuntimeError: If version fetch fails
        """
        try:
            # Use npm registry API which is more reliable
            api_url = f"https://registry.npmjs.org/{package_name}/latest"
            self.logger.debug(
                f"Fetching latest version for {package_name} from {api_url}"
            )

            request = Request(
                api_url,
                headers={"User-Agent": "frontend-updater/1.0"},
            )

            with urlopen(request) as response:
                data = json.loads(response.read().decode())

            if "version" not in data:
                raise RuntimeError(f"No version found for {package_name}")

            latest_version = data["version"]
            self.logger.debug(f"Latest version for {package_name}: {latest_version}")
            return latest_version

        except (URLError, HTTPError, json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"Failed to get latest version for {package_name}: {e}")

    def _download_file(self, url: str, dest_path: Path) -> None:
        """Download a file from URL to destination path.

        Args:
            url: URL to download from
            dest_path: Local path to save the file

        Raises:
            RuntimeError: If download fails
        """
        try:
            self.logger.debug(f"Downloading {url}")

            # Create a request with user agent to avoid potential blocking
            request = Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/91.0.4472.124 Safari/537.36"
                    )
                },
            )

            with urlopen(request) as response:
                content = response.read()

            # Ensure parent directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Remove existing file if it exists
            if dest_path.exists():
                dest_path.unlink()

            # Write file
            with open(dest_path, "wb") as f:
                f.write(content)

            self.logger.debug(f"Downloaded {dest_path.name}")

        except (URLError, HTTPError) as e:
            raise RuntimeError(f"Failed to download {url}: {e}")

    def update_library(self, library_name: str) -> None:
        """Update a specific library from CDN.

        Args:
            library_name: Name of the library to update

        Raises:
            ValueError: If library is not recognized
            RuntimeError: If update fails
        """
        if library_name not in LIBRARIES:
            raise ValueError(f"Unknown library: {library_name}")

        config = LIBRARIES[library_name]

        # Get latest version dynamically
        version = self._get_latest_version(config["package"])
        cdn_base = config["cdn_base"].format(version=version)

        self.logger.info(f"Updating {library_name} to latest version {version}...")

        # Create library directory
        lib_dir = self.vendor_dir / library_name
        lib_dir.mkdir(parents=True, exist_ok=True)

        # Download each file
        for remote_path, local_path in config["files"]:
            url = cdn_base + remote_path
            dest_path = lib_dir / local_path

            try:
                self._download_file(url, dest_path)
                self.logger.info(f"Downloaded {local_path}")
            except RuntimeError as e:
                self.logger.error(f"Failed to download {local_path}: {e}")
                raise

        self.logger.info(f"{library_name} updated successfully")

    def update_all(self) -> None:
        """Update all libraries."""
        self.logger.info("Updating all frontend dependencies...")

        for library_name in LIBRARIES:
            try:
                self.update_library(library_name)
            except Exception as e:
                self.logger.error(f"Failed to update {library_name}: {e}")
                raise

        self.logger.info("All libraries updated successfully!")

    def get_status(self) -> Dict[str, bool]:
        """Get installation status of all libraries.

        Returns:
            Dictionary mapping library names to installation status
        """
        status = {}

        for library_name, config in LIBRARIES.items():
            lib_dir = self.vendor_dir / library_name

            if not lib_dir.exists():
                status[library_name] = False
                continue

            # Check if all required files exist
            all_files_exist = True
            for _, local_path in config["files"]:
                if not (lib_dir / local_path).exists():
                    all_files_exist = False
                    break

            status[library_name] = all_files_exist

        return status


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Update frontend dependencies (Bootstrap, Chart.js, etc.)"
    )
    parser.add_argument(
        "library",
        nargs="?",
        choices=["all", "bootstrap", "bootstrap-icons", "chartjs"],
        default="all",
        help="Library to update (or 'all' for all libraries)",
    )
    parser.add_argument(
        "--vendor-dir",
        type=Path,
        default=VENDOR_DIR,
        help="Path to vendor directory",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List current installation status",
    )

    args = parser.parse_args()

    updater = FrontendUpdater(args.vendor_dir)

    print("Updating frontend dependencies...")
    print(f"Vendor directory: {args.vendor_dir}")
    print("-" * 50)

    if args.list:
        status = updater.get_status()
        print("Current installation status:")
        print("-" * 40)
        for lib_name, installed in status.items():
            status_str = "installed" if installed else "not installed"
            print(f"{lib_name:<20} {status_str}")
        return

    try:
        if args.library == "all":
            updater.update_all()
        else:
            updater.update_library(args.library)

        print("\nUpdate completed successfully!")

    except Exception as e:
        print(f"\nUpdate failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
