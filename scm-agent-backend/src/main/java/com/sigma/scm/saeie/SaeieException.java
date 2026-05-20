package com.sigma.scm.saeie;

public class SaeieException extends RuntimeException {
    public SaeieException(String message) {
        super(message);
    }

    public SaeieException(String message, Throwable cause) {
        super(message, cause);
    }

    public static class ConflictException extends SaeieException {
        public ConflictException(String message) { super(message); }
    }

    public static class InvalidStateTransitionException extends SaeieException {
        public InvalidStateTransitionException(String message) { super(message); }
    }

    public static class HeaderDriftException extends SaeieException {
        public HeaderDriftException(String message) { super(message); }
    }

    public static class FileTooLargeException extends SaeieException {
        public FileTooLargeException(String message) { super(message); }
    }

    public static class ValidationPayloadTooLargeException extends SaeieException {
        public ValidationPayloadTooLargeException(String message) { super(message); }
    }

    public static class SnapshotDecodeException extends SaeieException {
        public SnapshotDecodeException(String message) { super(message); }
    }
}
