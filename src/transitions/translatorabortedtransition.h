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

#ifndef TRANSLATORABORTEDTRANSITION_H
#define TRANSLATORABORTEDTRANSITION_H

#include <QSignalTransition>

/**
 * @brief Fires once a translator's in-flight request has finished or was aborted.
 *
 * Templated on the translator type so it works both with QOnlineTranslator and any
 * drop-in replacement (e.g. GoogleCloudTranslator) that exposes the same
 * `finished()` signal and `bool isRunning() const`.
 */
template<typename Translator>
class TranslatorAbortedTransition : public QSignalTransition
{
public:
    explicit TranslatorAbortedTransition(Translator *translator, QState *sourceState = nullptr)
        : QSignalTransition(translator, &Translator::finished, sourceState)
        , m_translator(translator)
    {
    }

protected:
    bool eventTest(QEvent *event) override
    {
        return !m_translator->isRunning() || QSignalTransition::eventTest(event);
    }

private:
    Translator *m_translator;
};

#endif // TRANSLATORABORTEDTRANSITION_H
