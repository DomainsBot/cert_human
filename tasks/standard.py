"""Tasks for standard operations needed by most projects."""

# Depend only on invoke and the standard library to easy initializing the project.
import os
from contextlib import suppress

from invoke import Context, task


@task()
def show_coverage(ctx: Context) -> None:
    """Shows coverage report."""
    ctx.run("coverage report", pty=True)


@task()
def mypy(ctx: Context) -> None:
    """Runs mypy."""
    ctx.run("mypy", pty=True)


# Extend the task with additional actions by populating pre or post tasks
# from a different module:
#     import tasks.standard; tasks.standard.test.pre.append(task(_start_server))
@task(pre=[mypy], post=[show_coverage])
def test(ctx: Context) -> None:
    from . import PROJECT_ROOT, TESTS_ROOT  # Avoid circular import.

    # Setting the start directory avoids scanning tasks, which configure
    # logging incorrectly for tests.
    ctx.run(
        f"PYTHONMALLOC=debug coverage run -m unittest discover --start-directory {TESTS_ROOT}"
        f" --top-level-directory {PROJECT_ROOT}",
        pty=True,
    )


@task()
def test_timing(_: Context) -> None:  # In 3.12, unittest can do this.
    """Runs test showing the slowest."""
    # module=None means discover.
    # verbosity>=2 starts displaying timing info.
    program = (
        "import unittest;"
        "from mamba_runner.runner import BlackMambaTestRunner;"
        "unittest.TestProgram("
        "    module=None,"
        "    testRunner=BlackMambaTestRunner,"
        "    verbosity=2,"
        ")"
    )
    # mamba_runner does not play well with invoke.
    os.execlp(
        "python",  # File to execute.
        # Argv.
        "python",
        "-c",
        program,
    )


@task()
def update_tldextract(_: Context) -> None:
    """Update TLDExtract, if installed."""
    with suppress(ImportError):
        import tldextract

        tldextract.TLDExtract().update()


@task(pre=[update_tldextract], post=[test])
def update(ctx: Context) -> None:
    """Pull, install reqs and test."""
    ctx.run("git pull || true")

    ctx.run(
        "aws --region us-east-1"
        " codeartifact login --tool pip --repository production --domain domainsbot-production"
        " --domain-owner 600475891916"
    )
    ctx.run("pip install -r dev-requirements.txt")

    # Update the pre-commit hooks then re-apply to the project files
    ctx.run("pre-commit autoupdate", pty=True)
    ctx.run("pre-commit run --all-files", pty=True)


@task(post=[update])
def setup(ctx: Context) -> None:
    """Setup the environment.

    Run on new repos or virtual environments.
    """
    ctx.run("pre-commit install --install-hooks")

    # Configure pip only within the virtualenv for DomainsBot.
    ctx.run("pip config --site set global.extra-index-url https://pypi.python.org/simple/")
    ctx.run("pip config --site set install.upgrade yes")
    ctx.run("pip config --site set install.upgrade-strategy eager")


@task()
def clean(ctx: Context) -> None:
    """Cleans build artifacts."""
    ctx.run("rm -rf dist/*")
    ctx.run("rm -rf ./*.egg-info")
    ctx.run("rm -rf build")


@task(post=[clean], pre=[clean])
def publish(ctx: Context) -> None:
    """Build and publish a package to DomainsBot's private repository."""
    ctx.run(
        "aws --region us-east-1 codeartifact login --tool twine --repository production"
        " --domain domainsbot-production --domain-owner 600475891916"
    )
    ctx.run("python setup.py bdist_wheel")
    ctx.run("TWINE_REPOSITORY=codeartifact twine upload dist/*")
