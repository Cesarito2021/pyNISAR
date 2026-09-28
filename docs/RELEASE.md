# Alpha publication

pyNISAR **0.1.0a1** was published on **28 September 2026** as a research alpha.
[PyPI](https://pypi.org/project/pyNISAR/0.1.0a1/) ·
[GitHub release](https://github.com/Cesarito2021/pyNISAR/releases/tag/v0.1.0a1) ·
[Successful publishing run](https://github.com/Cesarito2021/pyNISAR/actions/runs/36450164568).
The manuscript remains under review. GPL-3.0-only is unchanged.

```bash
python -m pip install pyNISAR==0.1.0a1
```

Validation: 38 local tests, successful wheel-install CI on Python 3.11–3.14,
and live NASA dual/quad CryoCloud runs. See [VALIDATION.md](VALIDATION.md).

## PyPI trusted publisher configuration

- Project: `pyNISAR`
- GitHub owner: `Cesarito2021`
- Repository: `pyNISAR`
- Workflow: `publish.yml`
- Environment: `pypi`

The publishing workflow runs only when manually dispatched for a version tag.
It verifies the tag, builds the distributions, installs the wheel, runs tests,
and checks metadata before publishing through PyPI Trusted Publishing. No API
key is committed. Ordinary pushes only run tests.
