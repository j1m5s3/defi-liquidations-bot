import hexbytes
from eth_abi import encode


def encode_path(path, path_types=None) -> str:
    """
    Encodes a path for use in a smart contract with param of type bytes
    :param path: list of values to encode
    :param path_types: list of types to encode values to
    :return:
    """
    if path_types is None:
        path_types = ["address", "uint24", "address", "uint24", "address", "uint24", "address"]

    # Encode the path
    try:
        # encoded_path = encode_packed(path_types, path)
        encoded_path = encode(path_types, path)
    except Exception as e:
        raise ValueError("Unable to encode path: {}".format(e))

    encoded_path_str = hexbytes.HexBytes(encoded_path).hex()

    return encoded_path_str
