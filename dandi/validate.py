import os.path
import os.path as op

from . import get_logger
from .consts import VIDEO_FILE_EXTENSIONS, dandiset_metadata_file
from .metadata import get_metadata
from .pynwb_utils import validate as pynwb_validate
from .pynwb_utils import validate_cache
from .utils import find_dandi_files, find_files, yaml_load

lgr = get_logger()

# TODO -- should come from schema.  This is just a simplistic example for now
_required_dandiset_metadata_fields = ["identifier", "name", "description"]
_required_nwb_metadata_fields = ["subject_id"]


# TODO: provide our own "errors" records, which would also include warnings etc
def validate(paths, schema_version=None, devel_debug=False, allow_any_path=False):
    """Validate content

    Parameters
    ----------
    paths: str or list of paths
      Could be individual (.nwb) files or a single dandiset path.

    Yields
    ------
    path, errors
      errors for a path
    """
    filepaths = find_files(".*", paths) if allow_any_path else find_dandi_files(paths)
    for path in filepaths:
        errors = validate_file(
            path, schema_version=schema_version, devel_debug=devel_debug
        )
        yield path, errors


def validate_file(filepath, schema_version=None, devel_debug=False):
    if op.basename(filepath) == dandiset_metadata_file:
        return validate_dandiset_yaml(
            filepath, schema_version=None, devel_debug=devel_debug
        )
    elif os.path.splitext(filepath)[-1] in VIDEO_FILE_EXTENSIONS:
        return validate_movie_file(filepath, devel_debug=devel_debug)
    else:
        return pynwb_validate(filepath, devel_debug=devel_debug) + validate_asset_file(
            filepath, schema_version=schema_version, devel_debug=devel_debug
        )


def validate_movie_file(filepath, devel_debug=False):
    try:
        import cv2
    except ImportError:
        lgr.error("could not validate video file as opencv is not installed")
        raise Exception(
            "do 'pip install opencv-python' to validate assisting video files"
        )

    if os.path.splitext(filepath)[-1] not in VIDEO_FILE_EXTENSIONS:
        msg = f"file ext must be one of supported types: {filepath}"
        if devel_debug:
            raise Exception(msg)
        lgr.warning(msg)

    try:
        cap = cv2.VideoCapture(str(filepath))
        if not cap.isOpened():
            msg = f"could not open video file {filepath} to validate"
            if devel_debug:
                raise Exception(msg)
            lgr.warning(msg)
            return [msg]
    except Exception as e:
        if devel_debug:
            raise
        lgr.warning("validation error %s for %s", e, filepath)
        return [str(e)]
    success, frame = cap.read()
    if success:
        return []
    else:
        return [f"no frames in video file {filepath}"]


@validate_cache.memoize_path
def validate_dandiset_yaml(filepath, schema_version=None, devel_debug=False):
    """Validate dandiset.yaml"""
    with open(filepath) as f:
        meta = yaml_load(f, typ="safe")
    if schema_version is None:
        schema_version = meta.get("schemaVersion")
    if schema_version is None:
        return _check_required_fields(meta, _required_dandiset_metadata_fields)
    else:
        from dandischema.models import Dandiset as DandisetMeta
        from dandischema.models import get_schema_version
        from pydantic import ValidationError

        current_version = get_schema_version()
        if schema_version != current_version:
            raise ValueError(
                f"Unsupported schema version: {schema_version}; expected {current_version}"
            )
        try:
            DandisetMeta(**meta)
        except ValidationError as e:
            if devel_debug:
                raise
            lgr.warning(
                "Validation error for %s: %s", filepath, e, extra={"validating": True}
            )
            return [str(e)]
        except Exception as e:
            if devel_debug:
                raise
            lgr.warning(
                "Unexpected validation error for %s: %s",
                filepath,
                e,
                extra={"validating": True},
            )
            return [f"Failed to initialize Dandiset meta: {e}"]
        return []


@validate_cache.memoize_path
def validate_asset_file(filepath, schema_version=None, devel_debug=False):
    """Provide validation of asset file regarding requirements we impose"""
    if schema_version is not None:
        from dandischema.models import BareAsset, get_schema_version
        from pydantic import ValidationError

        from .metadata import get_asset_metadata

        current_version = get_schema_version()
        if schema_version != current_version:
            raise ValueError(
                f"Unsupported schema version: {schema_version}; expected {current_version}"
            )
        try:
            asset = get_asset_metadata(
                filepath,
                relpath="dummy",
                digest=32 * "d" + "-1",
                digest_type="dandi_etag",
                allow_any_path=True,
            )
            BareAsset(**asset.dict())
        except ValidationError as e:
            if devel_debug:
                raise
            lgr.warning(
                "Validation error for %s: %s", filepath, e, extra={"validating": True}
            )
            return [str(e)]
        except Exception as e:
            if devel_debug:
                raise
            lgr.warning(
                "Unexpected validation error for %s: %s",
                filepath,
                e,
                extra={"validating": True},
            )
            return [f"Failed to read metadata: {e}"]
        return []
    else:
        # make sure that we have some basic metadata fields we require
        try:
            meta = get_metadata(filepath)
        except Exception as e:
            if devel_debug:
                raise
            lgr.warning(
                "Failed to read metadata in %s: %s",
                filepath,
                e,
                extra={"validating": True},
            )
            return [f"Failed to read metadata: {e}"]
        return _check_required_fields(meta, _required_nwb_metadata_fields)


def _check_required_fields(d, required):
    errors = []
    for f in required:
        v = d.get(f, None)
        if not v or (isinstance(v, str) and not (v.strip())):
            errors += [f"Required field {f!r} has no value"]
        if v in ("REQUIRED", "PLACEHOLDER"):
            errors += [f"Required field {f!r} has value {v!r}"]
    return errors
