from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_example_figures_and_navigation():
    app=AppTest.from_file(str(Path(__file__).parents[1]/'streamlit_app.py'),default_timeout=60).run()
    assert not app.exception
    assert any(m.value=='18' for m in app.metric)
    app.sidebar.selectbox[1].select('quad').run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert app.success
    app.sidebar.radio[0].set_value('Figures').run()
    assert not app.exception
    app.sidebar.radio[0].set_value('About & cite').run()
    assert not app.exception
    app.sidebar.radio[0].set_value('Find observations').run()
    assert not app.exception
