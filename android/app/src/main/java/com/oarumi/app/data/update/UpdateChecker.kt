package com.oarumi.app.data.update

import com.oarumi.app.data.net.HttpFetch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

/** Asks GitHub for the latest release. Nothing is downloaded by this class. */
@Singleton
class UpdateChecker
    @Inject
    constructor() {
        /** Swappable for tests. */
        internal var fetch: (String) -> String = { url ->
            HttpFetch.bytes(url, accept = "application/vnd.github+json").toString(Charsets.UTF_8)
        }

        suspend fun check(
            installedVersion: String,
            flavor: String,
        ): UpdateStatus =
            withContext(Dispatchers.IO) {
                decideUpdate(fetch(RELEASES_LATEST_URL), installedVersion, flavor)
            }

        companion object {
            const val RELEASES_LATEST_URL = "https://api.github.com/repos/LoopyLuci/oarumi/releases/latest"
        }
    }
