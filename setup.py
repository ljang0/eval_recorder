from pathlib import Path

from setuptools import setup


README = Path(__file__).with_name("README.md").read_text(encoding="utf-8")


setup(
    name="human-browser-trajectory-recorder",
    version="0.2.2",
    description="CLI for recording human browser trajectories as Playwright traces",
    long_description=README,
    long_description_content_type="text/markdown",
    py_modules=["human_browser_trajectory_recorder"],
    python_requires=">=3.10",
    install_requires=["playwright>=1.40,<2", "pynput>=1.7,<2"],
    entry_points={
        "console_scripts": [
            "human-browser-recorder=human_browser_trajectory_recorder:main",
        ]
    },
)
