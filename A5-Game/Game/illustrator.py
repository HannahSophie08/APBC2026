import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np


class Illustrator:
    def __init__(self, m, vizfile, framerate, theme='default'):
        self.robotspos = []
        self.robotshealth = []
        self.robotsmoney = []
        self.goldpos = []
        self.goldamount = []
        self.minepos = []
        self.minetime = []

        self.width = m.width
        self.height = m.height
        self.markersize = (200*900)/(self.width*self.height)
        self.linewidth = (7*900)/(self.width*self.height)

        self.find_walls(m)

        self.FRAME_PER_SECOND = framerate
        self.vizfile = vizfile

         # set theme, if no theme is given, use default
        if theme in self.THEMES:
            self.theme = self.THEMES[theme]
        else:
            print(f"Unknown theme '{theme}', using default.")
            self.theme = self.THEMES['default']
    
    # themes defining the appearance of the wall tiles 
    # wall_image: optional PNG that is added to each wall tile
    # zoom: defines scale of PNG on wall tiles
    # default: no wall_image 
    THEMES = {
        'default': {
            'wall_color': None,
            'wall_edge': None,
            'wall_image': None,
            'zoom': None,
            'mine_image': None,
            'gold_image': None
        },
        'desert': {
            'wall_color': "#F9F2D2",
            'wall_edge': "#BDA557",
            'wall_image': 'illustrations/cactus.png',
            'zoom': '0.024',
            'mine_image': 'illustrations/expl.png',
            'gold_image': 'illustrations/sand_gold.png',
            'floor_color': "#F9E6D2"
        },
        'forest': {
            'wall_color': '#c8e6c9',
            'wall_edge': '#388e3c',
            'wall_image': 'illustrations/evergreen_forest.png',
            'zoom': '0.024',
            'mine_image': 'illustrations/hole.png',
            'gold_image': 'illustrations/grass_gold.png',
            'floor_color': "#d8eed8"
        },
        'garden': {
            'wall_color': '#f0f4c3',
            'wall_edge': '#afb42b',
            'wall_image': 'illustrations/garden_wall.png',
            'zoom': '0.012',
            'mine_image': 'illustrations/hole.png',
            'gold_image': 'illustrations/grass_gold.png',
            'floor_color': "#c0dabd"
            
        },
        'island': {
            'wall_color': "#F5DD90",
            'wall_edge': "#6B3A13",
            'wall_image': 'illustrations/palm.png',
            'zoom': '0.024',
            'mine_image': 'illustrations/expl.png',
            'gold_image': 'illustrations/sand_gold.png',
            'floor_color': "#9ed0e1"
        }
    }

    def find_walls(self, m):
        self.walls = [
            (x, y)
            for y, row in enumerate(m._data)
            for x, tile in enumerate(row)
            if str(tile) == '#'
        ]

    def _add_robots(self, robots):
        self.n_robots = len(robots)
        self.robot_names = [robot.player_name for robot in robots]

    def _add_nrounds(self, rounds):
        self.n_rounds = rounds

    def append_robots(self, robots):
        rpos, rhealth, rmoney = [], [], []
        for robot in robots:
            rpos.append([robot.status.x, robot.status.y])
            rhealth.append(robot.status.health)
            rmoney.append(robot.status.gold)

        maxmoney = max(rmoney)
        rmoney = [80*money/maxmoney+25 for money in rmoney]

        self.robotspos.append(rpos)
        self.robotshealth.append(rhealth)
        self.robotsmoney.append(rmoney)

    def append_goldpots(self, goldpots):
        self.goldpos.append(list(goldpots.keys()))
        self.goldamount.append(list(goldpots.values()))

    def append_mines(self, mines):
        minepos = list(mines.keys()) + [(-1,-1)]
        minepos = minepos*5
        minepos = minepos[:5]
        self.minepos.append(minepos)
        self.minetime.append(list(mines.values()))

    def _illustrate(self):

        fig, self.ax = plt.subplots(
            nrows=1, ncols=1, figsize=(8, 8))
        fig.subplots_adjust(top=0.92, bottom=0.28)

        self.init_plot()
        self.init_walls()

        # --- Draw walls only once and not at every frame to make the animation faster ---

        fig.canvas.draw() # make sure walls are drawn
        extent = self.ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
        # safe area inside the axis as png
        plt.savefig('background.png', dpi=200, bbox_inches=extent)

        self.ax.cla()
        self.init_plot()  # restore axis limits
        # paste backround image as background
        bg_img = plt.imread('background.png')
        self.ax.imshow(bg_img, extent=[-0.5, self.width-0.5, -0.5, self.height-0.5],
                    origin='upper', zorder=0)
        # explicitly restore limits in case imshow changed them
        self.ax.set_ylim(top=self.height-0.5, bottom=-0.5)
        self.ax.set_xlim(left=-0.5, right=self.width-0.5)

        self.init_robots()
        self.init_trails()
        self.init_goldpots()
        self.init_mines()

        gif = FuncAnimation(fig, self.illustrate_round,
                            self.n_rounds)
        gif.save(self.vizfile, 
                 dpi=200, fps=self.FRAME_PER_SECOND) # higher dpi 

    def init_plot(self):
        self.ax.tick_params(
            bottom=False,
            left=False)
        self.ax.set_yticklabels([])
        self.ax.set_xticklabels([])

        self.ax.set_ylim(top=self.height-0.5, bottom=-0.5)
        self.ax.set_xlim(left=-0.5, right=self.width-0.5)

    def init_walls(self):
        x_coords, y_coords = list(zip(*self.walls))
        wall_set = set(self.walls)
        
        # find all diagonal gaps
        gap_x, gap_y = [], []
        seen_gaps = set()
        for (x, y) in self.walls:
            for dx, dy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
                diagonal = (x+dx, y+dy)
                if diagonal in wall_set:
                    if (x+dx, y) not in wall_set and (x, y+dy) not in wall_set:
                        gap = (x + dx*0.5, y + dy*0.5)
                        if gap not in seen_gaps:
                            seen_gaps.add(gap)
                            gap_x.append(gap[0])
                            gap_y.append(gap[1])

        if self.theme['wall_image'] is not None: # if theme is not default
            # emojis as files found in illustrations folder (source and if we need to look up: https://www.geeksforgeeks.org/python/working-with-images-in-python-using-matplotlib/)
            wall_img = plt.imread(self.theme['wall_image'])
            # walling our walls
            self.ax.scatter(x=x_coords, y=y_coords, marker='s', c=self.theme['wall_color'], s=self.markersize, linewidths=0.5, edgecolors=self.theme['wall_edge'])
            # we have to draw it for each tile (check out https://matplotlib.org/stable/gallery/text_labels_and_annotations/demo_annotation_box.html)
            for (x, y) in self.walls:
                imagebox = OffsetImage(wall_img, zoom=float(self.theme['zoom'])) # loading image
                box = AnnotationBbox(imagebox, (x, y), frameon=False) # placing image as coordinate
                self.ax.add_artist(box) # we need add_artist to add it to the plot
            
        else: # default theme 
            self.ax.scatter(x=x_coords, y=y_coords, marker='s', c='#8888aa',
                            s=self.markersize, edgecolors='#555577', linewidths=1.5)
            
        # draw gap indicators at diagonal gaps 
        if gap_x:
            self.ax.scatter(x=gap_x, y=gap_y, marker='+', c='white', s=self.markersize * 0.15, zorder=3, alpha=0.6)

        # draw floor tiles on non-wall cells, slightly transparent
        if self.theme.get('floor_color') is not None:
            wall_set = set(self.walls)
            floor_x, floor_y = [], []
            for x in range(self.width):
                for y in range(self.height):
                    if (x, y) not in wall_set:
                        floor_x.append(x)
                        floor_y.append(y)
            self.ax.scatter(x=floor_x, y=floor_y, marker='s', c=self.theme['floor_color'],
                            s=self.markersize, alpha=0.5, zorder=0)

    # different colors for each robot
    COLORS = ['#00ffff', '#ff6b6b', '#6bff6b', '#ffaa00', '#aa6bff', '#ff69b4', '#ff4500']

    def init_trails(self):
        self.trails = [
            self.ax.plot([], [], color = self.COLORS[i], alpha=0.5, linewidth=self.linewidth,zorder=1, label=self.robot_names[i])[0]
            for i in range(self.n_robots)
        ]

        # robot legend at the bottom in every theme () max 4 per row then wrap)
        robot_img = plt.imread('illustrations/robot_3.png')
        per_row = 4
        # "Players" title above the legend rows
        self.ax.text(0, -1.6, 'Players', ha='left', va='top',
                     fontsize=10, fontweight='bold', clip_on=False)
        for i in range(self.n_robots):
            row = i // per_row
            col = i % per_row
            # fixed spacing, packed from the left
            x = 3 + col * 7
            y = -4.2 - row * 5   # each extra row goes further down
            tinted = self.tint_image(robot_img, self.COLORS[i])
            imagebox = OffsetImage(tinted, zoom=0.055)   # small enough to fit a row nicely
            box = AnnotationBbox(imagebox, (x, y), frameon=False, annotation_clip=False)
            self.ax.add_artist(box)
            # name under each robot
            self.ax.text(x, y - 2.2, self.robot_names[i], ha='center', va='top',
                         fontsize=7, clip_on=False)

    # different markers for each robot 
    MARKERS = ['o', 'D', '^', 's', 'P', 'h', '*']

    def init_robots(self):
        # health ring goes green to red with health
        self.robot_outlines = []
        for i in range(self.n_robots):
            outline = self.ax.scatter(x=[], y=[], marker='o', vmin=0, vmax=100,
                        c=[], cmap='RdYlGn', zorder=2)
            self.robot_outlines.append(outline)

        # robots are now tinted images in every theme --> default included
        # load the grey robot and tinte it but only once 
        robot_img = plt.imread('illustrations/robot.png')
        self.robot_boxes = []
        for i in range(self.n_robots):
            tinted = self.tint_image(robot_img, self.COLORS[i])
            imagebox = OffsetImage(tinted, zoom=0.03)
            box = AnnotationBbox(imagebox, (0, 0), frameon=False, zorder=3)
            box.set_visible(False)   # hidden until the robot needs it
            self.ax.add_artist(box)
            self.robot_boxes.append(box)

    def tint_image(self, img, color):
        # tint only the light parts dark parts stay neutral
        # img is RGBA (0-1 floats)
        from matplotlib.colors import to_rgb
        r, g, b = to_rgb(color)
        tinted = img.copy()
        # brightness of each pixel
        strength = img[:, :, :3].mean(axis=2)
        tinted[:, :, 0] = img[:, :, 0] * (1 - strength) + r * strength
        tinted[:, :, 1] = img[:, :, 1] * (1 - strength) + g * strength
        tinted[:, :, 2] = img[:, :, 2] * (1 - strength) + b * strength
        # alpha channel stays untouched so transparency in background is kept
        return tinted

    def init_goldpots(self):
        # glow circle behind the pot, this is what pulses (easier and more readable than pulsing image)
        self.goldglow = self.ax.scatter(x=[], y=[], marker='o', c='gold', alpha=0.3, zorder=1)

        if self.theme['gold_image'] is not None:   # themed: pot is an image
            # we dont know the max pot count up front --> take account for that 
            max_pots = max(len(pots) for pots in self.goldpos)
            pot_img = plt.imread(self.theme['gold_image'])
            self.gold_boxes = []
            for _ in range(max_pots):
                imagebox = OffsetImage(pot_img, zoom=0.018)
                box = AnnotationBbox(imagebox, (0, 0), frameon=False, zorder=3)
                box.set_visible(False)   # hidden until a pot needs it
                self.ax.add_artist(box)
                self.gold_boxes.append(box)
        else:   # default: plain star, like before
            self.gold_boxes = None
            self.goldpots = self.ax.scatter(x=[], y=[], marker='*', edgecolors='k', c='gold')


    def init_mines(self):
        if self.theme['mine_image'] is not None:   # themed: mine is an image
            mine_img = plt.imread(self.theme['mine_image'])
            self.mine_boxes = []
            for _ in range(5):
                imagebox = OffsetImage(mine_img, zoom=0.03)
                box = AnnotationBbox(imagebox, (0, 0), frameon=False, zorder=4)
                box.set_visible(False)   # hidden until a mine needs it
                self.ax.add_artist(box)
                self.mine_boxes.append(box)
        else:   # default: plain red X, like before
            self.mine_boxes = None
            self.mines = self.ax.scatter(x=[], y=[], marker='X', edgecolors='k', c='red')

    def illustrate_round(self, i):
        def pivot(array):
            return list(zip(*array))

        if not (i+1) % 10:
            print('illustrating step', i+1)

        # counter, top left
        title = 'Counter: ' + str(i+1)
        self.ax.set_title(title, fontsize=16, loc='left')

        # goldpots
        sizes = []
        # pulse drives the glow circle, faster + bigger the older the pot
        for amount in self.goldamount[i]:
            pulse_speed = 0.5 + (amount / 200.0) * 0.5
            pulse = 1.0 + 0.4 * np.sin(i * pulse_speed)
            sizes.append(amount * pulse)

        # glow circle is the same in both themes
        self.goldglow.set_offsets(self.goldpos[i] if self.goldpos[i] else np.empty((0, 2)))
        self.goldglow.set_sizes([s * 3 for s in sizes] if sizes else [])

        if self.gold_boxes is not None:   # themed: move pot images, hide extras
            for j, box in enumerate(self.gold_boxes):
                if j < len(self.goldpos[i]):
                    box.xybox = self.goldpos[i][j]
                    box.xy = self.goldpos[i][j]
                    box.set_visible(True)
                else:
                    box.set_visible(False)
        else:   # default: plain star scatter
            self.goldpots.set_offsets(self.goldpos[i] if self.goldpos[i] else np.empty((0, 2)))
            self.goldpots.set_sizes(sizes if sizes else [])

        # robots: move robot images, ring shows health
        for j, (outline, box) in enumerate(zip(self.robot_outlines, self.robot_boxes)):
            pos = [self.robotspos[i][j]]
            size = self.robotsmoney[i][j]
            outline.set_offsets(pos)
            outline.set_sizes([size * 1.6]) # larger, so the health ring peeks out behind the robot
            outline.set_array(np.array([self.robotshealth[i][j]]))
            box.xybox = self.robotspos[i][j]
            box.xy = self.robotspos[i][j]
            box.set_visible(True)
            
        # mines
        if self.mine_boxes is not None:   # themed: move mine images, hide the rest
            mines_this_frame = self.minepos[i]
            for box, pos in zip(self.mine_boxes, mines_this_frame):
                if pos == (-1, -1):          # padding --> not a real mine, hide it
                    box.set_visible(False)
                else:
                    box.xybox = pos          # move the image
                    box.xy = pos
                    box.set_visible(True)
        else:   # default: plain red X scatter
            self.mines.set_offsets(self.minepos[i])

        # trails
        lo = [0, i-5][i-5 >= 0]
        offsets = pivot(self.robotspos[lo:i+1])
        for trail, offset in zip(self.trails, offsets):
            x, y = pivot(list(offset))
            trail.set_data(list(x), list(y))