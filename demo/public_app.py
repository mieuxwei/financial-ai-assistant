"""Zero-secret, fixture-only entrypoint for the R1A public research demo."""

from demo.app import render

render(public_release=True)
