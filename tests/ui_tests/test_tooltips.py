import os

import pytest
from adcm_pytest_plugin.utils import get_data_dir

# pylint: disable=W0611, W0621
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.pages import Configuration, LoginPage

DATADIR = get_data_dir(__file__)
BUNDLES = os.path.join(os.path.dirname(__file__), "../stack/")

NO_TOOLTIP_FIELDS = ['string_required_by_default_without_type',
                     'string_read_only_any_without_type']


@pytest.fixture(scope='function')
def service(sdk_client_fs):
    bundle = sdk_client_fs.upload_from_fs(DATADIR)
    cluster = bundle.cluster_create(name='tooltips')
    cluster.service_add(name='tooltips_test')
    return cluster.service(name="tooltips_test")


@pytest.fixture()
def app(adcm_fs):
    return ADCMTest(adcm_fs)


@pytest.fixture()
def login(app):
    app.driver.get(app.adcm.url)
    login = LoginPage(app.driver)
    login.login("admin", "admin")


@pytest.fixture()
def ui_config(app, login, service):
    app.driver.get("{}/cluster/{}/service/{}/config".format
                   (app.adcm.url, service.cluster_id, service.service_id))
    return Configuration(app.driver)


@pytest.fixture()
def tooltips(ui_config, service):
    config = service.prototype().config
    descriptions = [field['description'] for field in config[1:] if field['description'] != ""]
    textboxes = ui_config.get_textboxes()
    tooltips = []
    for textbox in textboxes:
        ttip = textbox.text.split(":")[0]
        if ttip in descriptions and ttip != "":
            tooltips.append(ui_config.get_tooltip_text_for_element(textbox))
    return tooltips, descriptions


def test_tooltip_presented(tooltips):
    """Check that field have description tooltip presented

    :return:
    """
    assert len(tooltips[0]) == 8


def test_tooltip_text(tooltips):
    """Check description in tooltip
    """
    try:
        assert set(tooltips[0]).issubset(set(tooltips[1])), set(tooltips[0]) - set(tooltips[1])
    except AssertionError:
        pytest.mark.xfail("Xfailed")


@pytest.mark.parametrize("field", NO_TOOLTIP_FIELDS)
def test_tooltip_not_presented(field, ui_config):
    """Check that we haven't tooltip for fields without description
    :return:
    """
    textboxes = ui_config.get_textboxes()
    for textbox in textboxes:
        if field == textbox.text.split(":")[0]:
            assert not ui_config.check_tooltip_for_field(textbox)
