import pathlib
import subprocess as process_execution
import sys as system_information


project_directory = pathlib.Path(__file__).resolve().parents[2]
cleaning_programs = (
    project_directory / "scripts" / "data_cleaning" / "build_site_data.py",
    project_directory / "scripts" / "data_cleaning" / "build_skill_reference.py",
    project_directory / "scripts" / "data_cleaning" / "build_learning_resources.py",
)


def run_cleaning_program(cleaning_program):
    process_execution.run(
        [system_information.executable, str(cleaning_program)],
        cwd=project_directory,
        check=True,
    )


def main():
    for cleaning_program in cleaning_programs:
        run_cleaning_program(cleaning_program)


if __name__ == "__main__":
    main()
