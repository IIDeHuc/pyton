import random, time, pygame, sys, copy
from pygame.locals import *

FPS = 30 # кадров в секунду для обновления экрана
WINDOWWIDTH = 600  # ширина окна программы, в пикселях
WINDOWHEIGHT = 600 # высота в пикселях

BOARDWIDTH = 8 # сколько столбцов на доске
BOARDHEIGHT = 8 # сколько строк в доске
GEMIMAGESIZE = 64 # ширина и высота каждого пространства в пикселях

# NUMGEMIMAGES - количество типов драгоценных камней. Вам понадобится изображение в формате .png
# файлы с именами gem0.png, gem1.png и т. д. до gem (N-1) .png.
NUMGEMIMAGES = 7
assert NUMGEMIMAGES >= 5 # игре нужно как минимум 5 видов драгоценных камней для работы

# NUMMATCHSOUNDS - это количество различных звуков на выбор, когда
# матч сделан. Файлы .wav называются match0.wav, match1.wav и т. Д.
NUMMATCHSOUNDS = 6

MOVERATE = 25 # От 1 до 100, большее число означает более быструю анимацию.
DEDUCTSPEED = 0.8 # снижает счет на 1 очко каждые DEDUCTSPEED секунды.

#             R    G    B
PURPLE    = (255,   0, 255)
LIGHTBLUE = (170, 190, 255)
BLUE      = (  0,   0, 255)
RED       = (255, 100, 100)
BLACK     = (  0,   0,   0)
BROWN     = ( 85,  65,   0)
HIGHLIGHTCOLOR = PURPLE # цвет границы выбранного камня
BGCOLOR = LIGHTBLUE # цвет фона на экране
GRIDCOLOR = BLUE # цвет игрового поля
GAMEOVERCOLOR = RED # цвет текста «Игра окончена».
GAMEOVERBGCOLOR = BLACK # цвет фона текста «Игра окончена».
SCORECOLOR = BROWN # цвет текста для счета игрока

# Количество места по бокам доски до края окна
# используется несколько раз, поэтому рассчитайте его здесь один раз и сохраните в переменных.
XMARGIN = int((WINDOWWIDTH - GEMIMAGESIZE * BOARDWIDTH) / 2)
YMARGIN = int((WINDOWHEIGHT - GEMIMAGESIZE * BOARDHEIGHT) / 2)

# константы для значений направления
UP = 'up'
DOWN = 'down'
LEFT = 'left'
RIGHT = 'right'

EMPTY_SPACE = -1 # произвольное неположительное значение
ROWABOVEBOARD = 'row above board' # произвольное, нецелое значение

def main():
    global FPSCLOCK, DISPLAYSURF, GEMIMAGES, GAMESOUNDS, BASICFONT, BOARDRECTS

    # Начальная настройка.
    pygame.init()
    FPSCLOCK = pygame.time.Clock()
    DISPLAYSURF = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
    pygame.display.set_caption('Gemgem')
    BASICFONT = pygame.font.Font('freesansbold.ttf', 36)

    # Загрузите изображения
    GEMIMAGES = []
    for i in range(1, NUMGEMIMAGES+1):
        gemImage = pygame.image.load('gem%s.png' % i)
        if gemImage.get_size() != (GEMIMAGESIZE, GEMIMAGESIZE):
            gemImage = pygame.transform.smoothscale(gemImage, (GEMIMAGESIZE, GEMIMAGESIZE))
        GEMIMAGES.append(gemImage)

    # Загрузите звуки.
    GAMESOUNDS = {}
    GAMESOUNDS['bad swap'] = pygame.mixer.Sound('badswap.wav')
    GAMESOUNDS['match'] = []
    for i in range(NUMMATCHSOUNDS):
        GAMESOUNDS['match'].append(pygame.mixer.Sound('match%s.wav' % i))

    # Создайте объекты pygame.Rect для каждого места на доске, чтобы
    # преобразовывать координаты платы в координаты пикселей.
    BOARDRECTS = []
    for x in range(BOARDWIDTH):
        BOARDRECTS.append([])
        for y in range(BOARDHEIGHT):
            r = pygame.Rect((XMARGIN + (x * GEMIMAGESIZE),
                             YMARGIN + (y * GEMIMAGESIZE),
                             GEMIMAGESIZE,
                             GEMIMAGESIZE))
            BOARDRECTS[x].append(r)

    while True:
        runGame()


def runGame():
    # Проходит одиночную игру. По окончании игры эта функция возвращается.

    # инициализировать доску
    gameBoard = getBlankBoard()
    score = 0
    fillBoardAndAnimate(gameBoard, [], score) # Бросьте начальные драгоценные камни.

    # инициализировать переменные для начала новой игры
    firstSelectedGem = None
    lastMouseDownX = None
    lastMouseDownY = None
    gameIsOver = False
    lastScoreDeduction = time.time()
    clickContinueTextSurf = None

    while True: # основной игровой цикл
        clickedSpace = None
        for event in pygame.event.get(): # цикл обработки событий
            if event.type == QUIT or (event.type == KEYUP and event.key == K_ESCAPE):
                pygame.quit()
                sys.exit()
            elif event.type == KEYUP and event.key == K_BACKSPACE:
                return # начать новую игру

            elif event.type == MOUSEBUTTONUP:
                if gameIsOver:
                    return # после окончания игры нажмите, чтобы начать новую игру

                if event.pos == (lastMouseDownX, lastMouseDownY):
                    # Это событие является щелчком мыши, а не окончанием ее перетаскивания.
                    clickedSpace = checkForGemClick(event.pos)
                else:
                    # это конец перетаскивания мышью
                    firstSelectedGem = checkForGemClick((lastMouseDownX, lastMouseDownY))
                    clickedSpace = checkForGemClick(event.pos)
                    if not firstSelectedGem or not clickedSpace:
                        # если не является частью допустимого перетаскивания, отмените выбор обоих
                        firstSelectedGem = None
                        clickedSpace = None
            elif event.type == MOUSEBUTTONDOWN:
                # это начало щелчка или перетаскивания мышью
                lastMouseDownX, lastMouseDownY = event.pos

        if clickedSpace and not firstSelectedGem:
            # Это был первый драгоценный камень, на который щелкнули.
            firstSelectedGem = clickedSpace
        elif clickedSpace and firstSelectedGem:
            # Щелкнули и выбрали два драгоценных камня. Поменяйте местами драгоценные камни.
            firstSwappingGem, secondSwappingGem = getSwappingGems(gameBoard, firstSelectedGem, clickedSpace)
            if firstSwappingGem == None and secondSwappingGem == None:
                # Если оба значения None, то драгоценные камни не были смежными.
                firstSelectedGem = None # снимите выделение с первого камня
                continue

            # Показать анимацию подкачки на экране.
            boardCopy = getBoardCopyMinusGems(gameBoard, (firstSwappingGem, secondSwappingGem))
            animateMovingGems(boardCopy, [firstSwappingGem, secondSwappingGem], [], score)

            # Поменяйте местами драгоценные камни в структуре данных доски.
            gameBoard[firstSwappingGem['x']][firstSwappingGem['y']] = secondSwappingGem['imageNum']
            gameBoard[secondSwappingGem['x']][secondSwappingGem['y']] = firstSwappingGem['imageNum']

            # Посмотрите, подходит ли это ход.
            matchedGems = findMatchingGems(gameBoard)
            if matchedGems == []:
                # Не было подходящего хода; обменять драгоценные камни обратно
                GAMESOUNDS['bad swap'].play()
                animateMovingGems(boardCopy, [firstSwappingGem, secondSwappingGem], [], score)
                gameBoard[firstSwappingGem['x']][firstSwappingGem['y']] = firstSwappingGem['imageNum']
                gameBoard[secondSwappingGem['x']][secondSwappingGem['y']] = secondSwappingGem['imageNum']
            else:
                # Это был подходящий ход.
                scoreAdd = 0
                while matchedGems != []:
                    # Удалите подобранные драгоценные камни, затем опустите доску.

                    # points - это список dicts, который сообщает fillBoardAndAnimate ()
                    # где на экране отображать текст, чтобы показать, сколько
                    # очков, набранных игроком. очков - это список, потому что если
                    # игрок получает несколько совпадений, затем должен появиться текст с несколькими точками.
                    points = []
                    for gemSet in matchedGems:
                        scoreAdd += (10 + (len(gemSet) - 3) * 10)
                        for gem in gemSet:
                            gameBoard[gem[0]][gem[1]] = EMPTY_SPACE
                        points.append({'points': scoreAdd,
                                       'x': gem[0] * GEMIMAGESIZE + XMARGIN,
                                       'y': gem[1] * GEMIMAGESIZE + YMARGIN})
                    random.choice(GAMESOUNDS['match']).play()
                    score += scoreAdd

                    # Бросьте новые драгоценные камни.
                    fillBoardAndAnimate(gameBoard, points, score)

                    # Проверьте, есть ли новые совпадения.
                    matchedGems = findMatchingGems(gameBoard)
            firstSelectedGem = None

            if not canMakeMove(gameBoard):
                gameIsOver = True

        # Нарисуйте доску.
        DISPLAYSURF.fill(BGCOLOR)
        drawBoard(gameBoard)
        if firstSelectedGem != None:
            highlightSpace(firstSelectedGem['x'], firstSelectedGem['y'])
        if gameIsOver:
            if clickContinueTextSurf == None:
                # Рендеринг текста выполняется только один раз. В будущих итерациях просто
                # использовать объект Surface уже в clickContinueTextSurf
                clickContinueTextSurf = BASICFONT.render('Final Score: %s (Click to continue)' % (score), 1, GAMEOVERCOLOR, GAMEOVERBGCOLOR)
                clickContinueTextRect = clickContinueTextSurf.get_rect()
                clickContinueTextRect.center = int(WINDOWWIDTH / 2), int(WINDOWHEIGHT / 2)
            DISPLAYSURF.blit(clickContinueTextSurf, clickContinueTextRect)
        elif score > 0 and time.time() - lastScoreDeduction > DEDUCTSPEED:
            # оценка падает со временем
            score -= 1
            lastScoreDeduction = time.time()
        drawScore(score)
        pygame.display.update()
        FPSCLOCK.tick(FPS)


def getSwappingGems(board, firstXY, secondXY):
    # Если драгоценные камни в координатах (X, Y) двух драгоценных камней находятся рядом,
    # затем их клавиши направления устанавливаются в соответствующее направление
    # значения, которые нужно поменять местами.
    # В противном случае возвращается (Нет, Нет).
    firstGem = {'imageNum': board[firstXY['x']][firstXY['y']],
                'x': firstXY['x'],
                'y': firstXY['y']}
    secondGem = {'imageNum': board[secondXY['x']][secondXY['y']],
                 'x': secondXY['x'],
                 'y': secondXY['y']}
    highlightedGem = None
    if firstGem['x'] == secondGem['x'] + 1 and firstGem['y'] == secondGem['y']:
        firstGem['direction'] = LEFT
        secondGem['direction'] = RIGHT
    elif firstGem['x'] == secondGem['x'] - 1 and firstGem['y'] == secondGem['y']:
        firstGem['direction'] = RIGHT
        secondGem['direction'] = LEFT
    elif firstGem['y'] == secondGem['y'] + 1 and firstGem['x'] == secondGem['x']:
        firstGem['direction'] = UP
        secondGem['direction'] = DOWN
    elif firstGem['y'] == secondGem['y'] - 1 and firstGem['x'] == secondGem['x']:
        firstGem['direction'] = DOWN
        secondGem['direction'] = UP
    else:
        # Эти драгоценные камни не находятся рядом и не могут быть обменены.
        return None, None
    return firstGem, secondGem


def getBlankBoard():
    # Создайте и верните пустую структуру данных доски.
    board = []
    for x in range(BOARDWIDTH):
        board.append([EMPTY_SPACE] * BOARDHEIGHT)
    return board


def canMakeMove(board):
    # Верните True, если плата находится в состоянии, в котором совпадают
    # по нему можно двигаться. В противном случае верните False.
    # Шаблоны в oneOffPatterns представляют собой драгоценные камни, которые настроены
    # таким образом, чтобы сделать тройку достаточно одного хода.
    oneOffPatterns = (((0,1), (1,0), (2,0)),
                      ((0,1), (1,1), (2,0)),
                      ((0,0), (1,1), (2,0)),
                      ((0,1), (1,0), (2,1)),
                      ((0,0), (1,0), (2,1)),
                      ((0,0), (1,1), (2,1)),
                      ((0,0), (0,2), (0,3)),
                      ((0,0), (0,1), (0,3)))

    # Переменные x и y перебирают каждое место на доске.
    # Если мы используем +, чтобы представить текущее итерируемое пространство на
    # доска, то этот шаблон: ((0,1), (1,0), (2,0)) относится к идентичным
    # драгоценные камни настраиваются следующим образом:
    #
    #     +A
    #     B
    #     C
    #
    # То есть драгоценный камень A смещен от + на (0,1), драгоценный камень B смещен
    # на (1,0), а драгоценный камень C смещен на (2,0). В этом случае самоцвет A может
    # быть переставленными влево, чтобы сформировать вертикальную тройку три в ряд.
    #
    # Есть восемь возможных способов сделать самоцветы одним ходом.
    # от образования тройки, следовательно, oneOffPattern имеет 8 паттернов.

    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT):
            for pat in oneOffPatterns:
                # проверьте каждый возможный шаблон "совпадение на следующем ходу", чтобы
                # посмотреть, можно ли сделать возможный ход.
                if (getGemAt(board, x+pat[0][0], y+pat[0][1]) == \
                    getGemAt(board, x+pat[1][0], y+pat[1][1]) == \
                    getGemAt(board, x+pat[2][0], y+pat[2][1]) != None) or \
                   (getGemAt(board, x+pat[0][1], y+pat[0][0]) == \
                    getGemAt(board, x+pat[1][1], y+pat[1][0]) == \
                    getGemAt(board, x+pat[2][1], y+pat[2][0]) != None):
                    return True # вернуть True при первом обнаружении шаблона
    return False


def drawMovingGem(gem, progress):
    # Нарисуйте драгоценный камень, скользящий в направлении, указанном на его клавише "направление".
    # указывает. Параметр прогресса - это число от 0 (просто
    # начиная) до 100 (слайд завершен).
    movex = 0
    movey = 0
    progress *= 0.01

    if gem['direction'] == UP:
        movey = -int(progress * GEMIMAGESIZE)
    elif gem['direction'] == DOWN:
        movey = int(progress * GEMIMAGESIZE)
    elif gem['direction'] == RIGHT:
        movex = int(progress * GEMIMAGESIZE)
    elif gem['direction'] == LEFT:
        movex = -int(progress * GEMIMAGESIZE)

    basex = gem['x']
    basey = gem['y']
    if basey == ROWABOVEBOARD:
        basey = -1

    pixelx = XMARGIN + (basex * GEMIMAGESIZE)
    pixely = YMARGIN + (basey * GEMIMAGESIZE)
    r = pygame.Rect( (pixelx + movex, pixely + movey, GEMIMAGESIZE, GEMIMAGESIZE) )
    DISPLAYSURF.blit(GEMIMAGES[gem['imageNum']], r)


def pullDownAllGems(board):
    # опускает драгоценные камни на доску вниз, чтобы заполнить все пробелы
    for x in range(BOARDWIDTH):
        gemsInColumn = []
        for y in range(BOARDHEIGHT):
            if board[x][y] != EMPTY_SPACE:
                gemsInColumn.append(board[x][y])
        board[x] = ([EMPTY_SPACE] * (BOARDHEIGHT - len(gemsInColumn))) + gemsInColumn


def getGemAt(board, x, y):
    if x < 0 or y < 0 or x >= BOARDWIDTH or y >= BOARDHEIGHT:
        return None
    else:
        return board[x][y]


def getDropSlots(board):
    # Создает «слот для перетаскивания» для каждого столбца и заполняет его
    # количество драгоценных камней, которых не хватает в этом столбце. Эта функция предполагает
    # что драгоценные камни уже были сброшены гравитацией.
    boardCopy = copy.deepcopy(board)
    pullDownAllGems(boardCopy)

    dropSlots = []
    for i in range(BOARDWIDTH):
        dropSlots.append([])

    # подсчитайте количество пустых мест в каждом столбце на доске
    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT-1, -1, -1): # начать снизу вверх
            if boardCopy[x][y] == EMPTY_SPACE:
                possibleGems = list(range(len(GEMIMAGES)))
                for offsetX, offsetY in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                    # Сузьте круг возможных драгоценных камней, которые мы должны вложить в
                    # пустое место, чтобы мы не вставили два из
                    # те же драгоценные камни рядом друг с другом, когда они падают.
                    neighborGem = getGemAt(boardCopy, x + offsetX, y + offsetY)
                    if neighborGem != None and neighborGem in possibleGems:
                        possibleGems.remove(neighborGem)

                newGem = random.choice(possibleGems)
                boardCopy[x][y] = newGem
                dropSlots[x].append(newGem)
    return dropSlots


def findMatchingGems(board):
    gemsToRemove = [] # список списков драгоценных камней в совпадающих триплетах, которые следует удалить
    boardCopy = copy.deepcopy(board)

    # пропустите каждое пространство, проверяя наличие 3-х смежных одинаковых драгоценных камней
    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT):
            # ищите горизонтальные совпадения
            if getGemAt(boardCopy, x, y) == getGemAt(boardCopy, x + 1, y) == getGemAt(boardCopy, x + 2, y) and getGemAt(boardCopy, x, y) != EMPTY_SPACE:
                targetGem = boardCopy[x][y]
                offset = 0
                removeSet = []
                while getGemAt(boardCopy, x + offset, y) == targetGem:
                    # продолжайте проверять, есть ли более 3 драгоценных камней подряд
                    removeSet.append((x + offset, y))
                    boardCopy[x + offset][y] = EMPTY_SPACE
                    offset += 1
                gemsToRemove.append(removeSet)

            # ищите вертикальные совпадения
            if getGemAt(boardCopy, x, y) == getGemAt(boardCopy, x, y + 1) == getGemAt(boardCopy, x, y + 2) and getGemAt(boardCopy, x, y) != EMPTY_SPACE:
                targetGem = boardCopy[x][y]
                offset = 0
                removeSet = []
                while getGemAt(boardCopy, x, y + offset) == targetGem:
                    # продолжайте проверять, если в ряду более 3 драгоценных камней
                    removeSet.append((x, y + offset))
                    boardCopy[x][y + offset] = EMPTY_SPACE
                    offset += 1
                gemsToRemove.append(removeSet)

    return gemsToRemove


def highlightSpace(x, y):
    pygame.draw.rect(DISPLAYSURF, HIGHLIGHTCOLOR, BOARDRECTS[x][y], 4)


def getDroppingGems(board):
    # Найдите все драгоценные камни, под которыми есть пустое место
    boardCopy = copy.deepcopy(board)
    droppingGems = []
    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT - 2, -1, -1):
            if boardCopy[x][y + 1] == EMPTY_SPACE and boardCopy[x][y] != EMPTY_SPACE:
                # Это пространство падает, если оно не пустое, но пространство под ним остается
                droppingGems.append( {'imageNum': boardCopy[x][y], 'x': x, 'y': y, 'direction': DOWN} )
                boardCopy[x][y] = EMPTY_SPACE
    return droppingGems


def animateMovingGems(board, gems, pointsText, score):
    # pointsText - это словарь с ключами 'x', 'y' и 'points'
    progress = 0 # прогресс в 0 означает начало, 100 означает завершение.
    while progress < 100: # цикл анимации
        DISPLAYSURF.fill(BGCOLOR)
        drawBoard(board)
        for gem in gems: # Нарисуйте каждый драгоценный камень.
            drawMovingGem(gem, progress)
        drawScore(score)
        for pointText in pointsText:
            pointsSurf = BASICFONT.render(str(pointText['points']), 1, SCORECOLOR)
            pointsRect = pointsSurf.get_rect()
            pointsRect.center = (pointText['x'], pointText['y'])
            DISPLAYSURF.blit(pointsSurf, pointsRect)

        pygame.display.update()
        FPSCLOCK.tick(FPS)
        progress += MOVERATE # немного продвинуть анимацию для следующего кадра


def moveGems(board, movingGems):
    # MovingGems - это список диктовок с клавишами x, y, direction, imageNum
    for gem in movingGems:
        if gem['y'] != ROWABOVEBOARD:
            board[gem['x']][gem['y']] = EMPTY_SPACE
            movex = 0
            movey = 0
            if gem['direction'] == LEFT:
                movex = -1
            elif gem['direction'] == RIGHT:
                movex = 1
            elif gem['direction'] == DOWN:
                movey = 1
            elif gem['direction'] == UP:
                movey = -1
            board[gem['x'] + movex][gem['y'] + movey] = gem['imageNum']
        else:
            # самоцвет находится над доской (откуда берутся новые самоцветы)
            board[gem['x']][0] = gem['imageNum'] # перейти в верхнюю строку


def fillBoardAndAnimate(board, points, score):
    dropSlots = getDropSlots(board)
    while dropSlots != [[]] * BOARDWIDTH:
        # сделайте анимацию падения, пока есть больше драгоценных камней
        movingGems = getDroppingGems(board)
        for x in range(len(dropSlots)):
            if len(dropSlots[x]) != 0:
                # заставляет самый низкий драгоценный камень в каждом слоте начать движение ВНИЗ
                movingGems.append({'imageNum': dropSlots[x][0], 'x': x, 'y': ROWABOVEBOARD, 'direction': DOWN})

        boardCopy = getBoardCopyMinusGems(board, movingGems)
        animateMovingGems(boardCopy, movingGems, points, score)
        moveGems(board, movingGems)

        # Сделайте следующий ряд драгоценных камней из слотов для выпадения
        # самый низкий, удалив предыдущие самые низкие драгоценные камни.
        for x in range(len(dropSlots)):
            if len(dropSlots[x]) == 0:
                continue
            board[x][0] = dropSlots[x][0]
            del dropSlots[x][0]


def checkForGemClick(pos):
    # Посмотрите, был ли щелчок мышью на доске
    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT):
            if BOARDRECTS[x][y].collidepoint(pos[0], pos[1]):
                return {'x': x, 'y': y}
    return None # Щелчка не было на доске.


def drawBoard(board):
    for x in range(BOARDWIDTH):
        for y in range(BOARDHEIGHT):
            pygame.draw.rect(DISPLAYSURF, GRIDCOLOR, BOARDRECTS[x][y], 1)
            gemToDraw = board[x][y]
            if gemToDraw != EMPTY_SPACE:
                DISPLAYSURF.blit(GEMIMAGES[gemToDraw], BOARDRECTS[x][y])


def getBoardCopyMinusGems(board, gems):
    # Создает и возвращает копию переданной структуры данных платы,
    # с удаленными драгоценными камнями в списке "драгоценных камней".
    #
    # Gems - это список dicts с клавишами x, y, direction, imageNum.

    boardCopy = copy.deepcopy(board)

    # Удалите некоторые драгоценные камни из этой копии структуры данных доски.
    for gem in gems:
        if gem['y'] != ROWABOVEBOARD:
            boardCopy[gem['x']][gem['y']] = EMPTY_SPACE
    return boardCopy


def drawScore(score):
    scoreImg = BASICFONT.render(str(score), 1, SCORECOLOR)
    scoreRect = scoreImg.get_rect()
    scoreRect.bottomleft = (10, WINDOWHEIGHT - 6)
    DISPLAYSURF.blit(scoreImg, scoreRect)


if __name__ == '__main__':
    main()
