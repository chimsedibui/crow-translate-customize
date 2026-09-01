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

#ifndef GOOGLECLOUDTRANSLATOR_H
#define GOOGLECLOUDTRANSLATOR_H

#include "qonlinetranslator.h"

#include <QJsonDocument>
#include <QPointer>

class QNetworkAccessManager;
class QNetworkReply;

/**
 * @brief Talks to the official Google Cloud Translation API (Basic v2, REST, API key auth)
 *        instead of the public web-scraping endpoint QOnlineTranslator's "Google" engine uses.
 *
 * Exposes the same subset of the QOnlineTranslator public API that the rest of the app
 * (MainWindow's state machine, TranslationEdit, Cli) relies on, so it can be used as a
 * drop-in replacement wherever that subset is templated on the translator type. Fields
 * the Cloud Translation Basic v2 API does not provide (transliteration, translation
 * options, examples) are always empty.
 */
class GoogleCloudTranslator : public QObject
{
    Q_OBJECT
    Q_DISABLE_COPY(GoogleCloudTranslator)

public:
    using Language = QOnlineTranslator::Language;
    using TranslationError = QOnlineTranslator::TranslationError;

    explicit GoogleCloudTranslator(QObject *parent = nullptr);

    void translate(const QString &text, Language translationLang = Language::Auto, Language sourceLang = Language::Auto);
    void detectLanguage(const QString &text);
    void abort();
    bool isRunning() const;

    QJsonDocument toJson() const;

    QString source() const;
    QString sourceTranslit() const;
    QString sourceTranscription() const;
    QString sourceLanguageName() const;
    Language sourceLanguage() const;

    QString translation() const;
    QString translationTranslit() const;
    QString translationLanguageName() const;
    Language translationLanguage() const;

    QMap<QString, QVector<QOption>> translationOptions() const;
    QMap<QString, QVector<QExample>> examples() const;

    TranslationError error() const;
    QString errorString() const;

    /**
     * @brief Whether a usable Google Cloud API key is configured in settings.
     *
     * Callers use this to decide whether to route the "Google" engine through this
     * class or fall back to QOnlineTranslator's built-in (scraped) Google engine.
     */
    static bool isConfigured();

signals:
    void finished();

private slots:
    void parseTranslateReply();
    void parseDetectReply();

private:
    void resetData(TranslationError error = TranslationError::NoError, const QString &errorString = {});
    void requestFailed(TranslationError error, const QString &errorString);
    QNetworkReply *post(const QUrl &url, const QJsonObject &body);

    /// Language code as expected by the Google Cloud Translation API (matches QOnlineTranslator's own Google exceptions, e.g. Hebrew -> "iw").
    static QString apiLanguageCode(Language lang);
    static Language languageFromApiCode(const QString &code);

    QNetworkAccessManager *m_networkManager;
    QPointer<QNetworkReply> m_currentReply;

    QString m_source;
    QString m_translation;
    Language m_sourceLang = Language::NoLanguage;
    Language m_translationLang = Language::NoLanguage;
    TranslationError m_error = TranslationError::NoError;
    QString m_errorString;
};

#endif // GOOGLECLOUDTRANSLATOR_H
