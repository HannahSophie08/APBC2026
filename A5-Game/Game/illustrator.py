import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import Rectangle # import needed for bar outline
import numpy as np
import os

# all asset paths are relative to this file, so it works no matter where the game is run from
_HERE = os.path.dirname(os.path.abspath(__file__))
def _asset(name):
    return os.path.join(_HERE, name)


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

        # if any png the theme needs cant be loaded, fall back to default
        # this way a missing/typo'd image doesnt crash the game, it just looks plain
        for key in ('wall_image', 'mine_image', 'gold_image'):
            path = self.theme.get(key)
            if path is None:
                continue
            try:
                plt.imread(path)
            except (FileNotFoundError, OSError):
                print(f"Could not load {path} for theme '{theme}', falling back to default theme.")
                self.theme = self.THEMES['default']
                break
    
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
            'wall_image': _asset('illustrations/cactus.png'),
            'zoom': '0.024',
            'mine_image': _asset('illustrations/expl.png'),
            'gold_image': _asset('illustrations/sand_gold.png'),
            'floor_color': "#F9E6D2"
        },
        'forest': {
            'wall_color': '#c8e6c9',
            'wall_edge': '#388e3c',
            'wall_image': _asset('illustrations/evergreen_forest.png'),
            'zoom': '0.024',
            'mine_image': _asset('illustrations/hole.png'),
            'gold_image': _asset('illustrations/grass_gold.png'),
            'floor_color': "#d8eed8"
        },
        'garden': {
            'wall_color': '#f0f4c3',
            'wall_edge': '#afb42b',
            'wall_image': _asset('illustrations/garden_wall.png'),
            'zoom': '0.012',
            'mine_image': _asset('illustrations/hole.png'),
            'gold_image': _asset('illustrations/grass_gold.png'),
            'floor_color': "#c0dabd"
            
        },
        'island': {
            'wall_color': "#F5DD90",
            'wall_edge': "#6B3A13",
            'wall_image': _asset('illustrations/palm.png'),
            'zoom': '0.024',
            'mine_image': _asset('illustrations/expl.png'),
            'gold_image': _asset('illustrations/sand_gold.png'),
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
        # hand-picked palette of distinguishable colours, used first
        # if there are more bots than we have hand-picked, fall back to hsv for the rest
        custom = [
            "#ff3f6f",  # red
            "#50ff67",  # green
            "#5378ff",  # blue
            "#ff9b54",  # orange
            "#cf33ff",  # purple
            '#42d4f4',  # cyan
            '#f032e6',  # magenta
            "#f0ff20",  # brown
            "#f8b4cd",  # pink
            '#469990',  # teal
            '#dcbeff',  # lavender
            '#800000',  # maroon
            '#aaffc3',  # mint
            '#808000',  # olive
            "#ffd900",  # yellow
        ]
        if self.n_robots <= len(custom):
            self.COLORS = custom[:self.n_robots]
        else:
            # fill the rest from hsv, skipping hues too close to ones we already have
            cmap = plt.get_cmap('hsv')
            extra = self.n_robots - len(custom)
            self.COLORS = custom + [cmap(i / extra) for i in range(extra)]

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
        per_row = 4
        rows = (self.n_robots + per_row - 1) // per_row

        # space the legend needs at the bottom, in inches
        legend_in = 1.4 + 0.9 * rows

        # tight side margins so the map fills the figure and we dont waste pixels on padding
        left_frac, right_frac, top_frac = 0.02, 0.98, 0.95

        # smaller figure --> less ram and the title/legend look bigger relative to the map
        # we still get the no-side-padding win from before
        fig_width = 7
        axes_in = fig_width * (right_frac - left_frac)
        fig_height = (axes_in + legend_in) / top_frac

        fig, self.ax = plt.subplots(nrows=1, ncols=1, figsize=(fig_width, fig_height))
        fig.subplots_adjust(left=left_frac, right=right_frac, top=top_frac, bottom=legend_in / fig_height)

        self.init_plot()
        # force the axes BOX to be square (not the datalim) so walls dont draw skewed
        self.ax.set_aspect('equal', adjustable='box')
        self.init_walls()

        # --- Draw walls only once and not at every frame to make the animation faster ---

        fig.canvas.draw() # make sure walls are drawn
        extent = self.ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
        # safe area inside the axis as png, use a temp file so we dont leave artifacts behind
        import tempfile
        bg_fd, bg_path = tempfile.mkstemp(suffix='.png')
        os.close(bg_fd)
        plt.savefig(bg_path, dpi=200, bbox_inches=extent)

        self.ax.cla()
        self.init_plot()  # restore axis limits
        self.ax.set_aspect('equal', adjustable='box')   # axes box stays square after cla
        # paste backround image as background
        bg_img = plt.imread(bg_path)
        try:
            os.remove(bg_path)   # clean up, we already have it in memory
        except OSError:
            pass
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
        gif.save(self.vizfile, dpi=200, fps=self.FRAME_PER_SECOND) # higher dpi 

    def init_plot(self):
        self.ax.tick_params(
            bottom=False,
            left=False)
        self.ax.set_yticklabels([])
        self.ax.set_xticklabels([])

        self.ax.set_ylim(top=self.height-0.5, bottom=-0.5)
        self.ax.set_xlim(left=-0.5, right=self.width-0.5)

        self.ax.set_aspect('equal', adjustable='box') # keep cells square no matter the figure shape

    def init_walls(self):
        wall_set = set(self.walls)

        # find all diagonal gaps (unchanged)
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

        # pick colors based on theme
        if self.theme['wall_image'] is not None:
            face = self.theme['wall_color']
            edge = self.theme['wall_edge']
            edge_lw = 0.5
        else:
            face = '#8888aa'
            edge = '#555577'
            edge_lw = 1.0

        # draw each wall as a 1x1 rectangle centered on its grid cell
        # Rectangle uses bottom-left corner, so shift by -0.5
        for (x, y) in self.walls:
            rect = Rectangle((x - 0.5, y - 0.5), 1, 1,
                            facecolor=face, edgecolor=edge,
                            linewidth=edge_lw, zorder=2)
            self.ax.add_patch(rect)

        # PNG overlay for themed mode (unchanged)
        if self.theme['wall_image'] is not None:
            wall_img = plt.imread(self.theme['wall_image'])
            for (x, y) in self.walls:
                imagebox = OffsetImage(wall_img, zoom=float(self.theme['zoom']))
                box = AnnotationBbox(imagebox, (x, y), frameon=False)
                self.ax.add_artist(box)

        # gap indicators (unchanged)
        if gap_x:
            self.ax.scatter(x=gap_x, y=gap_y, marker='+', c='white',
                            s=self.markersize * 0.15, zorder=3, alpha=0.6)

        # floor tiles — also Rectangles for the same reason
        if self.theme.get('floor_color') is not None:
            for x in range(self.width):
                for y in range(self.height):
                    if (x, y) not in wall_set:
                        rect = Rectangle((x - 0.5, y - 0.5), 1, 1,
                                        facecolor=self.theme['floor_color'],
                                        edgecolor='none',
                                        alpha=0.5, zorder=0)
                        self.ax.add_patch(rect)

    def init_trails(self):
        self.trails = [
            self.ax.plot([], [], color = self.COLORS[i], alpha=0.5, linewidth=self.linewidth,zorder=1, label=self.robot_names[i])[0]
            for i in range(self.n_robots)
        ]

        # robot legend at the bottom in every theme () max 4 per row then wrap)
        # if the legend png is missing we fall back to a plain matplotlib legend
        try:
            plt.imread(_asset('illustrations/robot.png'))
            plt.imread(_asset('illustrations/robot_3.png'))
            robot_img = plt.imread(_asset('illustrations/robot_3.png'))
        except (FileNotFoundError, OSError):
            robot_img = None
        if robot_img is None:
            legend_handles = [
                plt.scatter(
                    [], [],
                    marker=self.MARKERS[i % len(self.MARKERS)],
                    color=self.COLORS[i],
                    edgecolors='black',
                    linewidths=1,
                    label=self.robot_names[i]
                )
                for i in range(self.n_robots)
            ]
            self.ax.legend(
                handles=legend_handles,
                loc='upper center',
                bbox_to_anchor=(0.5, -0.12),
                ncol=min(4, self.n_robots),
                prop=dict(size=11),
                framealpha=0.75
            )
            return
        
        per_row = 4
        # shrink legend robots and tighten rows when there are many so they fit
        rows = (self.n_robots + per_row - 1) // per_row
        if rows <= 2:
            legend_zoom, row_step, name_fontsize, name_gap = 0.055, 5.0, 12, 2.2
        elif rows == 3:
            legend_zoom, row_step, name_fontsize, name_gap = 0.045, 4.5, 10, 2.0
        else:   # 4+ rows
            legend_zoom, row_step, name_fontsize, name_gap = 0.035, 3.8, 9, 1.6
        # "Players" title above the legend rows
        self.ax.text(0, -1.6, 'Players', ha='left', va='top',
                     fontsize=18, fontweight='bold', clip_on=False)
        for i in range(self.n_robots):
            row = i // per_row
            col = i % per_row
            # fixed spacing, packed from the left
            x = 3 + col * 7
            y = -4.2 - row * row_step   # each extra row goes further down
            tinted = self.tint_image(robot_img, self.COLORS[i])
            imagebox = OffsetImage(tinted, zoom=legend_zoom)   # small enough to fit a row nicely
            box = AnnotationBbox(imagebox, (x, y), frameon=False, annotation_clip=False)
            self.ax.add_artist(box)
            # name under each robot
            self.ax.text(x, y - name_gap, self.robot_names[i], ha='center', va='top',
                         fontsize=name_fontsize, clip_on=False)

    # different markers for each robot 
    MARKERS = ['o', 'D', '^', 's', 'P', 'h', '*']

    def init_robots(self):
        # hp bar instead of ring (since hasnt been implemented)
        self.hp_bg = []
        self.hp_fg = []
        for i in range(self.n_robots):
            bg = Rectangle((0, 0), 1, 0.22, facecolor='#333333', edgecolor='black', linewidth=1.5, zorder=4) # 0.22 is bar thigckness, linewidth outline thickness
            fg = Rectangle((0, 0), 1, 0.22, facecolor="#3edf30", edgecolor='none', zorder=5)
            self.ax.add_patch(bg)
            self.ax.add_patch(fg)
            self.hp_bg.append(bg)
            self.hp_fg.append(fg)

        # robots are now tinted images in every theme --> default included
        # load the grey robot and tinte it but only once
        # if the robot png is missing we fall back to plain shape markers so the game still runs
        try:
            robot_img = plt.imread(_asset('illustrations/robot.png'))
        except (FileNotFoundError, OSError):
            robot_img = None
        self.robot_boxes = []
        self.robot_markers = []
        if robot_img is not None:
            for i in range(self.n_robots):
                tinted = self.tint_image(robot_img, self.COLORS[i])
                imagebox = OffsetImage(tinted, zoom=0.032)
                box = AnnotationBbox(imagebox, (0, 0), frameon=False, zorder=3)
                box.set_visible(False)   # hidden until the robot needs it
                self.ax.add_artist(box)
                self.robot_boxes.append(box)
        else:   # fallback: plain shape markers like in the very first version
            for i in range(self.n_robots):
                marker = self.ax.scatter(x=[], y=[], marker=self.MARKERS[i % len(self.MARKERS)],
                    color=self.COLORS[i], edgecolors='black', linewidths=1, zorder=3)
                self.robot_markers.append(marker)

    def tint_image(self, img, color):
        # tint only the light parts dark parts stay neutral
        # img is RGBA (0-1 floats)
        from matplotlib.colors import to_rgb
        r, g, b = to_rgb(color)
        tinted = img.copy()
        # brightness of each pixel
        strength = img[:, :, :3].mean(axis=2)
        boost = strength ** 0.5
         # bias colour intensity towards colour not grex
        tinted[:, :, 0] = img[:, :, 0] * (1 - boost) + r * boost
        tinted[:, :, 1] = img[:, :, 1] * (1 - boost) + g * boost
        tinted[:, :, 2] = img[:, :, 2] * (1 - boost) + b * boost
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

        # robot --> move robot images, hp bar above shows health
        # if no robot image was loaded we fall back to the shape markers
        if self.robot_boxes:
            for j, box in enumerate(self.robot_boxes):
                box.xybox = self.robotspos[i][j]
                box.xy = self.robotspos[i][j]
                box.set_visible(True)
        else:   # fallback markers
            for j, marker in enumerate(self.robot_markers):
                pos = [self.robotspos[i][j]]
                size = self.robotsmoney[i][j]
                marker.set_offsets(pos)
                marker.set_sizes([size])

        # hp bar above each robot
        for j in range(self.n_robots):
            rx, ry = self.robotspos[i][j]
            hp = self.robotshealth[i][j]
            bar_y = ry + 0.7
            bar_w = 1.1
            self.hp_bg[j].set_xy((rx - bar_w/2, bar_y))
            self.hp_bg[j].set_width(bar_w)
            self.hp_fg[j].set_xy((rx - bar_w/2, bar_y))
            self.hp_fg[j].set_width(bar_w * (hp / 100))
            
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