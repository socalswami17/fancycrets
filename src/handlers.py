import base64
import json
import kopf
import kubernetes
import logging


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S')
CLIENT = None
LOGGER = logging.getLogger(__name__)


def make_get_client():
    global CLIENT
    if not CLIENT:
        LOGGER.info('creating k8s client')
        CLIENT = kubernetes.client.CoreV1Api()
    return CLIENT


def make_patch(data, annotations, namespace):
    patch_spec = {
        'sources': [],
        'formats': {},
    }
    red_secrets = {}
    patch = {}
    for k, v in annotations.items():
        if k.startswith('fancycrets.'):
            if k.startswith('fancycrets.secretSource.'):
                LOGGER.info("found secretSource %s", v)
                patch_spec['sources'].append(v)
            elif k.startswith('fancycrets.secretFormat.'):
                k2 = k[24:]
                LOGGER.info("found secretFormat  %s='%s'", k2, v)
                patch_spec['formats'][k2] = v

    client = make_get_client()
    for key in patch_spec['sources']:
        secret_dict = client.read_namespaced_secret(key, namespace).to_dict()['data']
        LOGGER.info("secret key %s has value %s", key, secret_dict)
        red_secret = {}
        for k, v in secret_dict.items():
            red_v = base64.b64decode(v).decode('utf-8')
            red_secret[k] = red_v
        red_secrets.update(red_secret)

    for key, format_string in patch_spec['formats'].items():
        red_secret = format_string.format(**red_secrets)
        patch[key] = base64.b64encode(red_secret.encode('utf-8')).decode('utf-8')

    patch.update(data)
    LOGGER.info("returning patch %s", patch)
    return patch


@kopf.on.create('secrets')
def create_secret(spec, name, namespace, logger, body, **kwargs):
    logger.info("created secret object named %s with spec %s", name, spec)
    if not kwargs:
        logger.info("no kwargs :shrug:")
        return

    logger.info("kwargs %s", kwargs)
    #annotations = body['metadata'].get('annotations')
    #patch = make_patch(annotations, namespace)
    #client = make_get_client()


@kopf.on.update('secrets')
def update_secret(spec, old, new, diff, logger, body, **kwargs):
    logger.info("updated secret with spec %s", spec)
    logger.info("old %s, new %s, diff %s", old, new, diff)
    logger.info("body %s", body)
    if not kwargs:
        logger.info("no kwargs :shrug:")
        return

    logger.info("kwargs %s", kwargs)
    fancycret_annotation = False
    for this_diff in diff:
        operation = this_diff[0]
        keys = this_diff[1]
        diff_remove = this_diff[2] or {}
        diff_add = this_diff[3] or {}
        logger.info("this diff: operation %s, keys %s, remove %s, add %s", operation, keys, diff_remove, diff_add)
        if keys[0] != 'metadata':
            logger.info("no metadata diff detected")
            continue
        if not diff_remove and not diff_add:
            logger.info("no diffs detected")
            continue
        annotations_remove = diff_remove.get('annotations') or {}
        annotations_add = diff_add.get('annotations') or {}
        if not annotations_remove and not annotations_add:
            logger.info("diff does not contain an annotations key")
            continue
        annotations_keys = list(annotations_remove.keys()) + list(annotations_add.keys())
        for annotations_key in annotations_keys:
            if annotations_key.startswith('fancycrets'):
                fancycret_annotation = True
                break

    if not fancycret_annotation:
        logger.info("fancycret annotation not found in diff dict")
        return

    annotations = body['metadata'].get('annotations')
    name = body['metadata'].get('name')
    namespace = body['metadata'].get('namespace')
    data = body['data']
    patch = make_patch(data, annotations, namespace)
    client = make_get_client()
    if not patch:
        logger.info("no patch")

    logger.info("updating myself with...myself")
    me_again = kubernetes.client.V1Secret(data=patch)
    client.patch_namespaced_secret(name, namespace, me_again)


@kopf.on.delete('secrets')
def delete_secret(spec, logger, body, **kwargs):
    logger.info("deleted secret with spec %s", spec)
    if kwargs:
        logger.info("kwargs %s", kwargs)


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.posting.level = logging.DEBUG
