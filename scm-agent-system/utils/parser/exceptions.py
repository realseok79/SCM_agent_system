# utils/parser/exceptions.py

class SAEIEError(Exception):
    """Base exception for SAEIE Engine"""
    pass

class NestedTransactionError(SAEIEError):
    """Raised when trying to start a business transaction inside an active transaction"""
    pass

class ConflictError(SAEIEError):
    """Raised when an optimistic lock conflict or mismatch is detected during status transition"""
    pass

class VersionOverflowError(SAEIEError):
    """Raised when version integer reaches the maximum limit and overflows"""
    pass

class InvalidStateTransitionError(SAEIEError):
    """Raised when an invalid state transition path is requested"""
    pass

class ValidationPayloadTooLargeError(SAEIEError):
    """Raised when validation payload size exceeds 2MB limit"""
    pass

class SnapshotDecodeError(SAEIEError):
    """Raised when gzip decompression safety limits are breached or stream concatenation is detected"""
    pass

class HeaderDriftError(SAEIEError):
    """Raised when unknown columns count exceeds 5 or DriftScore exceeds 0.5"""
    pass

class FileTooLargeError(SAEIEError):
    """Raised when source file size exceeds 50MB"""
    pass
