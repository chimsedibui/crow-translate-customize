/*
 *  Copyright © 2018-2023 Hennadii Chernyshchyk <genaloner@gmail.com>
 *
 *  This file is part of Crow Translate.
 *
 *  Crow Translate is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  Crow Translate is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with Crow Translate. If not, see <https://www.gnu.org/licenses/>.
 */

#include "googlecloudtranslator.h"

#include "settings/appsettings.h"

#include <QJsonArray>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrlQuery>

namespace
{
constexpr char s_apiBaseUrl[] = "https://translation.googleapis.com/language/translate/v2";
}

GoogleCloudTranslator::GoogleCloudTranslator(QObject *parent)
    : QObject(parent)
    , m_networkManager(new QNetworkAccessManager(this))
{
}

bool GoogleCloudTranslator::isConfigured()
{
    return !AppSettings().googleCloudApiKey().isEmpty();
}

void GoogleCloudTranslator::translate(const QString &text, Language translationLang, Language sourceLang)
{
    resetData();
    m_source = text;
    m_translationLang = translationLang;

    if (translationLang == Language::Auto) {
        requestFailed(TranslationError::ParametersError, tr("Unable to determine the translation language"));
        return;
    }

    QJsonObject body{
        {"q", text},
        {"target", apiLanguageCode(translationLang)},
        {"format", "text"},
    };
    if (sourceLang != Language::Auto) {
        body.insert("source", apiLanguageCode(sourceLang));
        m_sourceLang = sourceLang;
    } else {
        m_sourceLang = Language::Auto; // Resolved from the reply's detectedSourceLanguage once it arrives
    }

    m_currentReply = post(QUrl(QString::fromLatin1(s_apiBaseUrl)), body);
    connect(m_currentReply, &QNetworkReply::finished, this, &GoogleCloudTranslator::parseTranslateReply);
}

void GoogleCloudTranslator::detectLanguage(const QString &text)
{
    resetData();
    m_source = text;

    const QJsonObject body{{"q", text}};
    m_currentReply = post(QUrl(QString::fromLatin1(s_apiBaseUrl) + QStringLiteral("/detect")), body);
    connect(m_currentReply, &QNetworkReply::finished, this, &GoogleCloudTranslator::parseDetectReply);
}

void GoogleCloudTranslator::abort()
{
    if (m_currentReply)
        m_currentReply->abort();
}

bool GoogleCloudTranslator::isRunning() const
{
    return m_currentReply && !m_currentReply->isFinished();
}

QNetworkReply *GoogleCloudTranslator::post(const QUrl &url, const QJsonObject &body)
{
    QUrl requestUrl = url;
    QUrlQuery query;
    query.addQueryItem(QStringLiteral("key"), QString::fromUtf8(AppSettings().googleCloudApiKey()));
    requestUrl.setQuery(query);

    QNetworkRequest request(requestUrl);
    request.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    return m_networkManager->post(request, QJsonDocument(body).toJson(QJsonDocument::Compact));
}

void GoogleCloudTranslator::parseTranslateReply()
{
    QNetworkReply *reply = m_currentReply;
    if (!reply)
        return;
    reply->deleteLater();

    if (reply->error() == QNetworkReply::OperationCanceledError) {
        emit finished(); // Aborted, TranslatorAbortedTransition-alike logic relies on finished() firing regardless
        return;
    }

    const QByteArray data = reply->readAll();
    if (reply->error() != QNetworkReply::NoError) {
        const QJsonObject errorObject = QJsonDocument::fromJson(data).object().value(QStringLiteral("error")).toObject();
        const QString message = errorObject.value(QStringLiteral("message")).toString(reply->errorString());
        requestFailed(TranslationError::NetworkError, message);
        return;
    }

    const QJsonObject translations = QJsonDocument::fromJson(data).object().value(QStringLiteral("data")).toObject();
    const QJsonArray translationArray = translations.value(QStringLiteral("translations")).toArray();
    if (translationArray.isEmpty()) {
        requestFailed(TranslationError::ParsingError, tr("Unable to parse Google Cloud Translation API response"));
        return;
    }

    const QJsonObject translationObject = translationArray.first().toObject();
    m_translation = translationObject.value(QStringLiteral("translatedText")).toString();

    if (m_sourceLang == Language::Auto) {
        const QString detected = translationObject.value(QStringLiteral("detectedSourceLanguage")).toString();
        m_sourceLang = detected.isEmpty() ? Language::Auto : languageFromApiCode(detected);
    }

    emit finished();
}

void GoogleCloudTranslator::parseDetectReply()
{
    QNetworkReply *reply = m_currentReply;
    if (!reply)
        return;
    reply->deleteLater();

    if (reply->error() == QNetworkReply::OperationCanceledError) {
        emit finished();
        return;
    }

    const QByteArray data = reply->readAll();
    if (reply->error() != QNetworkReply::NoError) {
        const QJsonObject errorObject = QJsonDocument::fromJson(data).object().value(QStringLiteral("error")).toObject();
        const QString message = errorObject.value(QStringLiteral("message")).toString(reply->errorString());
        requestFailed(TranslationError::NetworkError, message);
        return;
    }

    const QJsonObject detectionsObject = QJsonDocument::fromJson(data).object().value(QStringLiteral("data")).toObject();
    const QJsonArray detectionsArray = detectionsObject.value(QStringLiteral("detections")).toArray();
    if (detectionsArray.isEmpty() || detectionsArray.first().toArray().isEmpty()) {
        requestFailed(TranslationError::ParsingError, tr("Unable to parse Google Cloud Translation API response"));
        return;
    }

    const QString code = detectionsArray.first().toArray().first().toObject().value(QStringLiteral("language")).toString();
    m_sourceLang = languageFromApiCode(code);
    emit finished();
}

void GoogleCloudTranslator::requestFailed(TranslationError error, const QString &errorString)
{
    m_error = error;
    m_errorString = errorString;
    emit finished();
}

void GoogleCloudTranslator::resetData(TranslationError error, const QString &errorString)
{
    m_source.clear();
    m_translation.clear();
    m_sourceLang = Language::NoLanguage;
    m_translationLang = Language::NoLanguage;
    m_error = error;
    m_errorString = errorString;
}

QString GoogleCloudTranslator::apiLanguageCode(Language lang)
{
    if (lang == Language::Hebrew)
        return QStringLiteral("iw"); // Matches QOnlineTranslator's own Google engine exception
    return QOnlineTranslator::languageCode(lang);
}

GoogleCloudTranslator::Language GoogleCloudTranslator::languageFromApiCode(const QString &code)
{
    if (code == QLatin1String("iw"))
        return Language::Hebrew;
    return QOnlineTranslator::language(code);
}

QJsonDocument GoogleCloudTranslator::toJson() const
{
    const QJsonObject object{
        {"examples", QJsonObject()},
        {"source", m_source},
        {"sourceTranscription", QString()},
        {"sourceTranslit", QString()},
        {"translation", m_translation},
        {"translationOptions", QJsonObject()},
        {"translationTranslit", QString()},
    };
    return QJsonDocument(object);
}

QString GoogleCloudTranslator::source() const
{
    return m_source;
}

QString GoogleCloudTranslator::sourceTranslit() const
{
    return {};
}

QString GoogleCloudTranslator::sourceTranscription() const
{
    return {};
}

QString GoogleCloudTranslator::sourceLanguageName() const
{
    return QOnlineTranslator::languageName(m_sourceLang);
}

GoogleCloudTranslator::Language GoogleCloudTranslator::sourceLanguage() const
{
    return m_sourceLang;
}

QString GoogleCloudTranslator::translation() const
{
    return m_translation;
}

QString GoogleCloudTranslator::translationTranslit() const
{
    return {};
}

QString GoogleCloudTranslator::translationLanguageName() const
{
    return QOnlineTranslator::languageName(m_translationLang);
}

GoogleCloudTranslator::Language GoogleCloudTranslator::translationLanguage() const
{
    return m_translationLang;
}

QMap<QString, QVector<QOption>> GoogleCloudTranslator::translationOptions() const
{
    return {};
}

QMap<QString, QVector<QExample>> GoogleCloudTranslator::examples() const
{
    return {};
}

GoogleCloudTranslator::TranslationError GoogleCloudTranslator::error() const
{
    return m_error;
}

QString GoogleCloudTranslator::errorString() const
{
    return m_errorString;
}
