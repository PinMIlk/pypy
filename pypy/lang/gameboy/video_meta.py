from pypy.lang.gameboy.constants import SPRITE_SIZE, MAX_SPRITES,\
                                        GAMEBOY_SCREEN_HEIGHT,\
                                        GAMEBOY_SCREEN_WIDTH

# Metadata visualizing windows.

class VideoMetaWindow(object):
    def __init__(self, gameboy, x, y):
        self.width = x
        self.height = y
        self.screen = [[0] * x for i in range(y)]
        self.gameboy = gameboy
        self.x = 0
        self.y = 0

    def get_screen(self):
        return self.screen

    def set_origin(self, x, y):
        self.x = x
        self.y = y

    def draw(self):
        self.update_screen()
        self.draw_on_driver()

    def update_screen(self):
        raise Exception("Not implemented")

    def draw_on_driver(self):
        for y in range(self.height):
            line = self.screen[y]
            for x in range(self.width):
                self.gameboy.video_driver.draw_pixel(x + self.x,
                                                     y + self.y,
                                                     self.gameboy.video.palette[self.screen[y][x]])

    def clear_screen(self):
        for line in self.screen:
            for x in range(len(line)):
                line[x] = 0

class TileDataWindow(VideoMetaWindow):
    def __init__(self, gameboy):
        self.tiles_x = 24
        self.tiles_y = 16
        VideoMetaWindow.__init__(self, gameboy,
                                       self.tiles_x * SPRITE_SIZE,
                                       self.tiles_y * SPRITE_SIZE)

    def update_screen(self):
        for y_id in range(self.tiles_y):
            for x_id in range(self.tiles_x):
                tile = self.gameboy.video.get_tile_at(x_id * self.tiles_y + y_id)
                for y_offset in range(SPRITE_SIZE):
                    line = self.screen[y_offset + y_id * SPRITE_SIZE]
                    tile.draw(line, x_id * SPRITE_SIZE, y_offset)

class PreviewWindow(VideoMetaWindow):
    def __init__(self, gameboy):
        VideoMetaWindow.__init__(self, gameboy,
                                       SPRITE_SIZE + GAMEBOY_SCREEN_WIDTH + SPRITE_SIZE,
                                       GAMEBOY_SCREEN_HEIGHT)

    def get_window(self):
        raise Exception("Not Implemented")

    def update_screen(self):
        for y in range(self.height):
            line = self.screen[y]
            self.gameboy.video.draw_window(self.get_window(), y, line)

class WindowPreview(PreviewWindow):
    def get_window(self):
        # XXX Broken for now
        return self.gameboy.video.window

class BackgroundPreview(PreviewWindow):
    def get_window(self):
        return self.gameboy.video.background

class SpriteWindow(VideoMetaWindow):
    def __init__(self, gameboy):
        self.sprites_y = 8
        self.sprites_x = MAX_SPRITES / self.sprites_y
        VideoMetaWindow.__init__(self, gameboy,
                                       self.sprites_x * SPRITE_SIZE,
                                       self.sprites_y * SPRITE_SIZE * 2) # Double sprites

    def update_screen(self):
        self.clear_screen()
        for y_id in range(self.sprites_y):
            for x_id in range(self.sprites_x):
                sprite = self.gameboy.video.get_sprite_at(y_id * self.sprites_x + x_id)
                for y_offset in range(SPRITE_SIZE * (1 + sprite.big_size)):
                    line = self.screen[y_offset + y_id * SPRITE_SIZE * 2]
                    tile = sprite.get_tile_for_relative_line(y_offset)
                    if sprite.y_flipped:
                        y_offset = SPRITE_SIZE - 1 - y_offset
                    tile.draw(line, x_id * SPRITE_SIZE, y_offset)
                    
                    for x in range(SPRITE_SIZE):
                        x += x_id * SPRITE_SIZE
                        line[x] = line[x] << 1 # Colors of sprites are in
                                               # another range of the palette.
