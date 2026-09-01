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

#ifndef TRANSLATORERRORTRANSITION_H
#define TRANSLATORERRORTRANSITION_H

#include "qonlinetranslator.h"

#include <QAbstractTransition>

/**
 * @brief Fires when a translator's last operation ended in an error.
 *
 * Templated so it works both with QOnlineTranslator and any drop-in replacement
 * (e.g. GoogleCloudTranslator) that exposes `error()` returning
 * QOnlineTranslator::TranslationError.
 */
template<typename Translator>
class TranslatorErrorTransition : public QAbstractTransition
{
public:
    explicit TranslatorErrorTransition(Translator *translator, QState *sourceState = nullptr)
        : QAbstractTransition(sourceState)
        , m_translator(translator)
    {
    }

protected:
    bool eventTest(QEvent *) override
    {
        return m_translator->error() != QOnlineTranslator::NoError;
    }

    void onTransition(QEvent *) override
    {
    }

private:
    Translator *m_translator;
};

#endif // TRANSLATORERRORTRANSITION_H
