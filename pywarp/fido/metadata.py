import base64
import json
from functools import lru_cache

import cryptography.hazmat.backends
import jwt
import requests
from cryptography import x509


class FIDOMetadataClient:
    mds_url = "https://mds.fidoalliance.org/"
    _metadata_toc = None

    @property
    def metadata_toc(self):
        if self._metadata_toc is None:
            res = requests.get(self.mds_url)
            res.raise_for_status()
            jwt_header = jwt.get_unverified_header(res.content)
            algorithm = jwt_header["alg"]
            assert algorithm in {"ES256", "RS256"}
            cert = x509.load_der_x509_certificate(
                jwt_header["x5c"][0].encode(), cryptography.hazmat.backends.default_backend()
            )
            # FIXME: test coverage
            self._metadata_toc = jwt.decode(res.content, key=cert.public_key(), algorithms=[algorithm])  # type: ignore
        return self._metadata_toc

    @lru_cache(64)
    def metadata_for_key_id(self, key_id):
        for e in self.metadata_toc["entries"]:
            if key_id in e.get("attestationCertificateKeyIdentifiers", []):
                break
        else:
            raise KeyError("No metadata found for key ID {}".format(key_id))
        res = requests.get(e["url"])
        res.raise_for_status()
        return json.loads(base64.b64decode(res.content).decode())
