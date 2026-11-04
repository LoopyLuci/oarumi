package oarumi.errors

open class OarumiException(message: String) : Exception(message)

class ValidationException(
    message: String,
    val errors: List<String> = emptyList(),
) : OarumiException(message)

class FallbackRequiredException(
    message: String,
    val component: String,
    val trigger: String,
) : OarumiException(message)

class OfflineException(message: String) : OarumiException(message)

class IntegrityException(message: String) : OarumiException(message)

class CapabilityMissingException(
    message: String,
    val capability: String,
) : OarumiException(message)
