"""
This test suite ensures the docstrings of class methods in
dirty_cat are formatted according to numpydoc specifications.
`DOCSTRING_TEMP_IGNORE_SET` defines a set of class methods
to skip while running the validation tests, so that CI will
not fail.
Therefore, developers having formatted methods to numpydoc
should also remove their corresponding references from the list.
"""
import inspect
import re
from importlib import import_module
from typing import Optional

import pytest
from numpydoc.validate import validate

DOCSTRING_TEMP_IGNORE_SET = {
    "dirty_cat._datetime_encoder.DatetimeEncoder.get_feature_names",
    "dirty_cat._datetime_encoder.DatetimeEncoder.get_feature_names_out",
    "dirty_cat._gap_encoder.GapEncoder.fit",
    "dirty_cat._gap_encoder.GapEncoder.get_feature_names",
    "dirty_cat._gap_encoder.GapEncoder.get_feature_names_out",
    "dirty_cat._gap_encoder.GapEncoder.partial_fit",
    "dirty_cat._gap_encoder.GapEncoder.score",
    "dirty_cat._gap_encoder.GapEncoder.transform",
    "dirty_cat._minhash_encoder.MinHashEncoder",
    "dirty_cat._minhash_encoder.MinHashEncoder.fit",
    "dirty_cat._minhash_encoder.MinHashEncoder._get_fast_hash",
    "dirty_cat._minhash_encoder.MinHashEncoder._get_murmur_hash",
    "dirty_cat._minhash_encoder.MinHashEncoder.transform",
    "dirty_cat._similarity_encoder.SimilarityEncoder",
    "dirty_cat._similarity_encoder.SimilarityEncoder.fit",
    "dirty_cat._similarity_encoder.SimilarityEncoder.transform",
    "dirty_cat._similarity_encoder.SimilarityEncoder.fit_transform",
    "dirty_cat._super_vectorizer.SuperVectorizer.fit_transform",
    "dirty_cat._super_vectorizer.SuperVectorizer.transform",
    "dirty_cat._super_vectorizer.SuperVectorizer._auto_cast",
    "dirty_cat._super_vectorizer.SuperVectorizer._apply_cast",
    "dirty_cat._super_vectorizer.SuperVectorizer.get_feature_names",
    "dirty_cat._super_vectorizer.SuperVectorizer.get_feature_names_out",
    "dirty_cat._target_encoder.TargetEncoder",
    "dirty_cat._target_encoder.TargetEncoder.fit",
    "dirty_cat._target_encoder.TargetEncoder.transform",
    # The following are not documented in dirty_cat (and thus are out of scope)
    # They are usually inherited from other libraries.
    "dirty_cat._super_vectorizer.SuperVectorizer.fit",
    "dirty_cat._super_vectorizer.SuperVectorizer.set_params",
    "dirty_cat._super_vectorizer.SuperVectorizer.named_transformers_",
}


def all_estimators():
    module = import_module("dirty_cat")
    classes = inspect.getmembers(module, inspect.isclass)
    classes = [(name, est_cls) for name, est_cls in classes if not name.startswith("_")]
    return sorted(classes, key=lambda x: x[0])


def get_all_methods():
    estimators = all_estimators()
    for name, Estimator in estimators:
        if name.startswith("_"):
            # skip private classes
            continue
        methods = []
        for name in dir(Estimator):
            if name.startswith("_"):
                continue
            method_obj = getattr(Estimator, name)
            if hasattr(method_obj, "__call__") or isinstance(method_obj, property):
                methods.append(name)
        methods.append(None)

        for method in sorted(methods, key=str):
            yield Estimator, method


def repr_errors(res, estimator=None, method: Optional[str] = None) -> str:
    """Pretty print original docstring and the obtained errors
    Parameters
    ----------
    res : dict
        result of numpydoc.validate.validate
    estimator : {estimator, None}
        estimator object or None
    method : str
        if estimator is not None, either the method name or None.
    Returns
    -------
    str
       String representation of the error.
    """
    if method is None:
        if hasattr(estimator, "__init__"):
            method = "__init__"
        elif estimator is None:
            raise ValueError("At least one of estimator, method should be provided")
        else:
            raise NotImplementedError

    if estimator is not None:
        obj = getattr(estimator, method)
        try:
            obj_signature = str(inspect.signature(obj))
        except TypeError:
            # In particular we can't parse the signature of properties
            obj_signature = (
                "\nParsing of the method signature failed, "
                "possibly because this is a property."
            )

        obj_name = estimator.__name__ + "." + method
    else:
        obj_signature = ""
        obj_name = method

    msg = "\n\n" + "\n\n".join(
        [
            str(res["file"]),
            obj_name + obj_signature,
            res["docstring"],
            "# Errors",
            "\n".join(
                " - {}: {}".format(code, message) for code, message in res["errors"]
            ),
        ]
    )
    return msg


def filter_errors(errors, method, Estimator=None):
    """
    Ignore some errors based on the method type.
    """
    for code, message in errors:
        # We ignore following error code,
        #  - RT02: The first line of the Returns section
        #    should contain only the type, ..
        #   (as we may need refer to the name of the returned
        #    object)
        #  - GL01: Docstring text (summary) should start in the line
        #    immediately after the opening quotes (not in the same line,
        #    or leaving a blank line in between)
        #  - GL02: If there's a blank line, it should be before the
        #    first line of the Returns section, not after (it allows to have
        #    short docstrings for properties).
        #  - SA01: See Also section not found
        #  - EX01: No examples section found; FIXME: remove when #373 resolved

        if code in ["RT02", "GL01", "GL02", "SA01", "EX01"]:
            continue

        # Following codes are only taken into account for the
        # top level class docstrings:
        #  - ES01: No extended summary found
        #  - EX01: No examples section found

        if method is not None and code in ["EX01", "ES01"]:
            continue

        yield code, message


@pytest.mark.parametrize("Estimator, method", get_all_methods())
def test_docstring(Estimator, method, request):
    base_import_path = Estimator.__module__
    import_path = [base_import_path, Estimator.__name__]
    if method is not None:
        import_path.append(method)

    import_path = ".".join(import_path)

    if import_path in DOCSTRING_TEMP_IGNORE_SET:
        request.applymarker(
            pytest.mark.xfail(run=False, reason="TODO pass numpydoc validation")
        )

    res = validate(import_path)

    res["errors"] = list(filter_errors(res["errors"], method, Estimator=Estimator))

    if res["errors"]:
        msg = repr_errors(res, Estimator, method)

        raise ValueError(msg)


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Validate docstrings with numpydoc.")
    parser.add_argument("import_path", help="Import path to validate")

    args = parser.parse_args()

    res = validate(args.import_path)

    import_path_sections = args.import_path.split(".")

    if len(import_path_sections) >= 2 and re.match(
        r"(?:[A-Z][a-z]*)+", import_path_sections[-2]
    ):
        method = import_path_sections[-1]
    else:
        method = None

    if res["errors"]:
        msg = repr_errors(res, method=args.import_path)

        print(msg)
        sys.exit(1)
    else:
        print("All docstring checks passed for {}!".format(args.import_path))
