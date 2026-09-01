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

#include "translationedit.h"

#include "contextmenu.h"

TranslationEdit::TranslationEdit(QWidget *parent)
    : QTextEdit(parent)
{
}

QString TranslationEdit::translation() const
{
    return m_translation;
}

QOnlineTranslator::Language TranslationEdit::translationLanguage()
{
    return m_lang;
}

void TranslationEdit::clearTranslation()
{
    if (!m_translation.isEmpty()) {
        m_translation.clear();
        m_lang = QOnlineTranslator::NoLanguage;
        emit translationEmpty(true);
    }
    clear();
}

void TranslationEdit::contextMenuEvent(QContextMenuEvent *event)
{
    auto *contextMenu = new ContextMenu(this, event);
    contextMenu->popup();
}
