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

#ifndef RETRANSLATIONTRANSITION_H
#define RETRANSLATIONTRANSITION_H

#include "languagebuttonswidget.h"
#include "qonlinetranslator.h"

#include <QAbstractTransition>

/**
 * @brief Fires when source and translation language ended up being the same after
 *        auto-detection, so the app should retranslate to the secondary language.
 *
 * Templated so it works both with QOnlineTranslator and any drop-in replacement
 * (e.g. GoogleCloudTranslator) that exposes `error()`, `sourceLanguage()` and
 * `translationLanguage()` matching QOnlineTranslator's.
 */
template<typename Translator>
class RetranslationTransition : public QAbstractTransition
{
public:
    RetranslationTransition(Translator *translator, LanguageButtonsWidget *buttons, QState *sourceState = nullptr)
        : QAbstractTransition(sourceState)
        , m_translator(translator)
        , m_langButtons(buttons)
    {
    }

protected:
    bool eventTest(QEvent *) override
    {
        // The NoLanguage check matters when a second, currently-unused translator instance
        // (e.g. an idle GoogleCloudTranslator while QOnlineTranslator is handling the
        // request, or vice versa) is wired into the same state as a parallel transition:
        // an untouched instance defaults source/translation language to the same
        // NoLanguage value, which would otherwise look like a false "source == translation" match.
        return m_translator->error() == QOnlineTranslator::NoError
            && m_translator->sourceLanguage() != QOnlineTranslator::NoLanguage
            && m_langButtons->isAutoButtonChecked()
            && m_translator->sourceLanguage() == m_translator->translationLanguage();
    }

    void onTransition(QEvent *) override
    {
    }

private:
    Translator *m_translator;
    LanguageButtonsWidget *m_langButtons;
};

#endif // RETRANSLATIONTRANSITION_H
