package oarumi.pivot

object Phrasebook {
    private val table: Map<String, Map<String, String>> =
        mapOf(
            "es" to
                mapOf(
                    "hola" to "hello",
                    "hola, mundo" to "hello, world",
                    "buenos días" to "good morning",
                    "buenas noches" to "good night",
                    "gracias" to "thank you",
                    "por favor" to "please",
                    "sí" to "yes",
                    "no" to "no",
                    "quiero agua" to "I want water",
                    "quiero comer" to "I want to eat",
                    "¿dónde está el baño?" to "where is the bathroom",
                    "¿cómo estás?" to "how are you",
                    "yo veo el libro" to "I see the book",
                    "él quiere ir" to "he wants to go",
                    "es bueno" to "it is good",
                    "es malo" to "it is bad",
                ),
            "fr" to
                mapOf(
                    "bonjour" to "hello",
                    "merci" to "thank you",
                    "s'il vous plaît" to "please",
                    "oui" to "yes",
                    "non" to "no",
                    "je veux de l'eau" to "I want water",
                    "je vois le livre" to "I see the book",
                    "il veut partir" to "he wants to go",
                    "c'est bon" to "it is good",
                    "c'est mauvais" to "it is bad",
                    "où sont les toilettes" to "where is the bathroom",
                    "comment ça va" to "how are you",
                ),
            "de" to
                mapOf(
                    "hallo" to "hello",
                    "danke" to "thank you",
                    "bitte" to "please",
                    "ja" to "yes",
                    "nein" to "no",
                    "ich will wasser" to "I want water",
                    "ich sehe das buch" to "I see the book",
                    "er will gehen" to "he wants to go",
                    "es ist gut" to "it is good",
                    "es ist schlecht" to "it is bad",
                    "wo ist die toilette" to "where is the bathroom",
                    "wie geht es dir" to "how are you",
                ),
            "zh" to
                mapOf(
                    "你好" to "hello",
                    "谢谢" to "thank you",
                    "请" to "please",
                    "是" to "yes",
                    "不" to "no",
                    "我要水" to "I want water",
                    "我看见书" to "I see the book",
                    "他想去" to "he wants to go",
                    "这是好的" to "it is good",
                    "这是坏的" to "it is bad",
                    "洗手间在哪里" to "where is the bathroom",
                    "你好吗" to "how are you",
                ),
            "ar" to
                mapOf(
                    "مرحبا" to "hello",
                    "شكرا" to "thank you",
                    "من فضلك" to "please",
                    "نعم" to "yes",
                    "لا" to "no",
                    "أريد الماء" to "I want water",
                    "أرى الكتاب" to "I see the book",
                    "يريد أن يذهب" to "he wants to go",
                    "إنه جيد" to "it is good",
                    "إنه سيء" to "it is bad",
                    "أين الحمام" to "where is the bathroom",
                    "كيف حالك" to "how are you",
                ),
        )

    fun lookup(
        lang: String,
        text: String,
    ): String? = table[lang]?.get(text.trim().lowercase())

    fun supportedLanguages(): List<String> = table.keys.sorted()
}
