from datetime import datetime
import json
import os
from pathlib import Path

from jsonschema import Draft6Validator
import pytest
import requests

from ..models import (
    AccessType,
    AssetMeta,
    DandisetMeta,
    DigestType,
    IdentifierType,
    LicenseType,
    ParticipantRelationType,
    PublishedDandisetMeta,
    RelationType,
    RoleType,
    to_datacite,
)

METADATA_DIR = Path(__file__).with_name("data") / "metadata"


def test_dandiset():
    assert DandisetMeta.unvalidated()


def test_asset():
    assert AssetMeta.unvalidated()


@pytest.mark.parametrize(
    "enumtype,values",
    [
        (
            AccessType,
            {
                "Open": "dandi:Open",
                "Embargoed": "dandi:Embargoed",
                "Restricted": "dandi:Restricted",
            },
        ),
        (
            RoleType,
            {
                "Author": "dandi:Author",
                "Conceptualization": "dandi:Conceptualization",
                "ContactPerson": "dandi:ContactPerson",
                "DataCollector": "dandi:DataCollector",
                "DataCurator": "dandi:DataCurator",
                "DataManager": "dandi:DataManager",
                "FormalAnalysis": "dandi:FormalAnalysis",
                "FundingAcquisition": "dandi:FundingAcquisition",
                "Investigation": "dandi:Investigation",
                "Maintainer": "dandi:Maintainer",
                "Methodology": "dandi:Methodology",
                "Producer": "dandi:Producer",
                "ProjectLeader": "dandi:ProjectLeader",
                "ProjectManager": "dandi:ProjectManager",
                "ProjectMember": "dandi:ProjectMember",
                "ProjectAdministration": "dandi:ProjectAdministration",
                "Researcher": "dandi:Researcher",
                "Resources": "dandi:Resources",
                "Software": "dandi:Software",
                "Supervision": "dandi:Supervision",
                "Validation": "dandi:Validation",
                "Visualization": "dandi:Visualization",
                "Funder": "dandi:Funder",
                "Sponsor": "dandi:Sponsor",
                "StudyParticipant": "dandi:StudyParticipant",
                "Affiliation": "dandi:Affiliation",
                "EthicsApproval": "dandi:EthicsApproval",
                "Other": "dandi:Other",
            },
        ),
        (
            RelationType,
            {
                "IsCitedBy": "dandi:IsCitedBy",
                "Cites": "dandi:Cites",
                "IsSupplementTo": "dandi:IsSupplementTo",
                "IsSupplementedBy": "dandi:IsSupplementedBy",
                "IsContinuedBy": "dandi:IsContinuedBy",
                "Continues": "dandi:Continues",
                "Describes": "dandi:Describes",
                "IsDescribedBy": "dandi:IsDescribedBy",
                "HasMetadata": "dandi:HasMetadata",
                "IsMetadataFor": "dandi:IsMetadataFor",
                "HasVersion": "dandi:HasVersion",
                "IsVersionOf": "dandi:IsVersionOf",
                "IsNewVersionOf": "dandi:IsNewVersionOf",
                "IsPreviousVersionOf": "dandi:IsPreviousVersionOf",
                "IsPartOf": "dandi:IsPartOf",
                "HasPart": "dandi:HasPart",
                "IsReferencedBy": "dandi:IsReferencedBy",
                "References": "dandi:References",
                "IsDocumentedBy": "dandi:IsDocumentedBy",
                "Documents": "dandi:Documents",
                "IsCompiledBy": "dandi:IsCompiledBy",
                "Compiles": "dandi:Compiles",
                "IsVariantFormOf": "dandi:IsVariantFormOf",
                "IsOriginalFormOf": "dandi:IsOriginalFormOf",
                "IsIdenticalTo": "dandi:IsIdenticalTo",
                "IsReviewedBy": "dandi:IsReviewedBy",
                "Reviews": "dandi:Reviews",
                "IsDerivedFrom": "dandi:IsDerivedFrom",
                "IsSourceOf": "dandi:IsSourceOf",
                "IsRequiredBy": "dandi:IsRequiredBy",
                "Requires": "dandi:Requires",
                "Obsoletes": "dandi:Obsoletes",
                "IsObsoletedBy": "dandi:IsObsoletedBy",
            },
        ),
        (
            ParticipantRelationType,
            {
                "IsChildOf": "dandi:IsChildOf",
                "IsDizygoticTwinOf": "dandi:IsDizygoticTwinOf",
                "IsMonozygoticTwinOf": "dandi:IsMonozygoticTwinOf",
                "IsSiblingOf": "dandi:IsSiblingOf",
                "isParentOf": "dandi:isParentOf",
            },
        ),
        (
            LicenseType,
            {
                "CC0_10": "spdx:CC0-1.0",
                "CC_BY_40": "spdx:CC-BY-4.0",
                "CC_BY_NC_40": "spdx:CC-BY-NC-4.0",
            },
        ),
        (
            IdentifierType,
            {
                "doi": "dandi:doi",
                "orcid": "dandi:orcid",
                "ror": "dandi:ror",
                "dandi": "dandi:dandi",
                "rrid": "dandi:rrid",
            },
        ),
        (
            DigestType,
            {
                "md5": "dandi:md5",
                "sha1": "dandi:sha1",
                "sha2_256": "dandi:sha2-256",
                "sha3_256": "dandi:sha3-256",
                "blake2b_256": "dandi:blake2b-256",
                "blake3": "dandi:blake3",
                "dandi_etag": "dandi:dandi-etag",
            },
        ),
    ],
)
def test_types(enumtype, values):
    assert {v.name: v.value for v in enumtype} == values


def test_autogenerated_titles():
    schema = AssetMeta.schema()
    assert schema["title"] == "Asset Meta"
    assert schema["properties"]["schemaVersion"]["title"] == "Schema Version"
    assert schema["definitions"]["PropertyValue"]["title"] == "Property Value"


def datacite_post(datacite, doi):
    """
    posting the datacite object and returning the status codes
    of requests.post and requests.get
    """

    # removing doi in case it exists
    _clean_doi(doi)

    # checking f I'm able to create doi
    rp = requests.post(
        "https://api.test.datacite.org/dois",
        json=datacite,
        headers={"Content-Type": "application/vnd.api+json"},
        auth=("DARTLIB.DANDI", os.environ["DATACITE_DEV_PASSWORD"]),
    )

    # checking if i'm able to get the url
    rg = requests.get(
        url=f"https://api.test.datacite.org/dois/{doi.replace('/','%2F')}/activities"
    )

    # cleaning url
    _clean_doi(doi)
    return rp.status_code, rg.status_code


def _clean_doi(doi):
    """removing doi, ignoring the status code"""
    requests.delete(
        f"https://api.test.datacite.org/dois/{doi.replace('/', '%2F')}",
        auth=("DARTLIB.DANDI", os.environ["DATACITE_DEV_PASSWORD"]),
    )


@pytest.fixture(scope="module")
def schema():
    sr = requests.get(
        "https://raw.githubusercontent.com/datacite/schema/master/source/"
        "json/kernel-4.3/datacite_4.3_schema.json"
    )
    schema = sr.json()
    return schema


@pytest.mark.parametrize("dandi_nr", ["000004", "000008"])
def test_datacite(dandi_nr, schema):
    """ checking to_datacite for a specific datasets"""
    prefix = "10.80507"
    version = "v.0"

    with (METADATA_DIR / f"newmeta{dandi_nr}.json").open() as f:
        newmeta_js = json.load(f)

    newmeta_js["doi"] = f"{prefix}/dandi.{dandi_nr}.{version}"
    newmeta_js["datePublished"] = str(datetime.now().year)
    newmeta_js["publishedBy"] = "https://doi.test.datacite.org/dois"
    newmeta_js["version"] = version
    newmeta = PublishedDandisetMeta(**newmeta_js)

    datacite = to_datacite(meta=newmeta)

    Draft6Validator.check_schema(schema)
    validator = Draft6Validator(schema)
    validator.validate(datacite["data"]["attributes"])

    # posting datacite, and checking status codes
    post_status_code, get_status_code = datacite_post(datacite, newmeta.doi)
    assert post_status_code == 201
    assert get_status_code == 200


def test_dantimeta_1():
    """ checking basic metadata for publishing"""
    # meta data without doi, datePublished and publishedBy
    meta_dict = {
        "identifier": "DANDI:912",
        "id": "DANDI:912/draft",
        "version": "v.1",
        "name": "testing dataset",
        "description": "testing",
        "contributor": [
            {
                "name": "last name, first name",
                "roleName": [RoleType("dandi:ContactPerson")],
            }
        ],
        "license": [LicenseType("spdx:CC-BY-4.0")],
    }

    # should work for DandisetMeta but PublishedDandisetMeta should raise an error
    DandisetMeta(**meta_dict)
    with pytest.raises(Exception) as exc:
        PublishedDandisetMeta(**meta_dict)

    assert [el["msg"] == "field required" for el in exc.value.errors()]
    assert set([el["loc"][0] for el in exc.value.errors()]) == {
        "datePublished",
        "publishedBy",
        "doi",
    }

    # after adding doi, datePublished, publishedBy, PublishedDandisetMeta should work
    meta_dict["doi"] = "00000"
    meta_dict["datePublished"] = str(datetime.now().year)
    meta_dict["publishedBy"] = "https://doi.test.datacite.org/dois"
    PublishedDandisetMeta(**meta_dict)


@pytest.mark.parametrize(
    "additional_meta, datacite_checks",
    [
        # no additional meta
        ({}, {"creators": (1, {"name": "A_last, A_first"})}),
        # additional contributor with dandi:Author
        (
            {
                "contributor": [
                    {
                        "name": "A_last, A_first",
                        "roleName": [RoleType("dandi:ContactPerson")],
                    },
                    {"name": "B_last, B_first", "roleName": [RoleType("dandi:Author")]},
                ],
            },
            {
                "creators": (1, {"name": "B_last, B_first"}),
                "contributors": (
                    1,
                    {"name": "A_last, A_first", "contributorType": "ContactPerson"},
                ),
            },
        ),
    ],
)
def test_dantimeta_datacite(schema, additional_meta, datacite_checks):
    """ checking datacite objects for specific metadata dictionaries"""

    prefix = "10.80507"
    version = "v.0"
    dandi_id = "DANDI:999"

    # meta data without doi, datePublished and publishedBy
    meta_dict = {
        "identifier": dandi_id,
        "id": f"{dandi_id}/draft",
        "version": version,
        "name": "testing dataset",
        "description": "testing",
        "contributor": [
            {
                "name": "A_last, A_first",
                "roleName": [RoleType("dandi:ContactPerson")],
            }
        ],
        "license": [LicenseType("spdx:CC-BY-4.0")],
        "publishedBy": "https://doi.test.datacite.org/dois",
        "datePublished": str(datetime.now().year),
        "doi": f"{prefix}/dandi.{dandi_id}.{version}",
    }
    meta_dict.update(additional_meta)

    # creating PublishedDandisetMeta from the dictionary
    meta = PublishedDandisetMeta(**meta_dict)
    # creating and validating datacite objects
    datacite = to_datacite(meta)
    Draft6Validator.check_schema(schema)
    validator = Draft6Validator(schema)
    validator.validate(datacite["data"]["attributes"])

    # checking some datacite fields
    attr = datacite["data"]["attributes"]
    for key, el in datacite_checks.items():
        el_len, el_flds = el
        if el_len:
            # checking length and some fields from the first element
            assert len(attr[key]) == el_len
            for k, v in el_flds.items():
                assert attr[key][0][k] == v
        else:
            for k, v in el_flds.items():
                assert attr[key][k] == v

    # posting datacite, and checking status codes
    post_status_code, get_status_code = datacite_post(datacite, meta.doi)
    assert post_status_code == 201
    assert get_status_code == 200
