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
        },
        'desert': {
            'wall_color': '#F9E6D2',
            'wall_edge': '#BD8057',
            'wall_image': 'illustrations/cactus.png',
            'zoom': 0.035,
        },
        'forest': {
            'wall_color': '#c8e6c9',
            'wall_edge': '#388e3c',
            'wall_image': 'illustrations/evergreen_forest.png',
            'zoom': '0.035'
        },
        'garden': {
            'wall_color': '#f0f4c3',
            'wall_edge': '#afb42b',
            'wall_image': 'illustrations/flowers.png',
            'zoom': '0.02'
        },
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
        fig.subplots_adjust(top=0.85)  

        self.init_plot()
        self.init_walls()

        # --- Draw walls only once and not at every frame to make the animation faster ---

        fig.canvas.draw() # make sure walls are drawn
        extent = self.ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
        # safe area inside the axis as png
        plt.savefig('background.png', dpi=100, bbox_inches=extent)

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
                 dpi=100, fps=self.FRAME_PER_SECOND) # higher dpi 

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
            self.ax.scatter(x=gap_x, y=gap_y, marker='o', c='white', s=self.markersize * 0.15, zorder=3, alpha=0.6)


    # different colors for each robot
    COLORS = ['#00ffff', '#ff6b6b', '#6bff6b', '#ffaa00', '#aa6bff', '#ff69b4', '#ff4500']

    def init_trails(self):
        self.trails = [
            self.ax.plot([], [], color = self.COLORS[i], alpha=0.5, linewidth=self.linewidth,zorder=1, label=self.robot_names[i])[0]
            for i in range(self.n_robots)
        ]
        legend_handles = [
            plt.scatter([], [], marker=self.MARKERS[i], c=self.COLORS[i],
                        edgecolors='black', linewidths=1, label=self.robot_names[i])
            for i in range(self.n_robots)
        ]
        self.ax.legend(handles=legend_handles, loc='lower left', bbox_to_anchor=(0.0, 1.0), prop=dict(size=8), framealpha = 0.7)

    # different markers for each robot 
    MARKERS = ['o', 'D', '^', 's', 'P', 'h', '*']

    def init_robots(self):
        self.robot_outlines = []
        self.robot_markers = []
        for i in range(self.n_robots):
            # colored outer ring in the color of the robot 
            outline = self.ax.scatter(x=[], y=[], marker=self.MARKERS[i], c=self.COLORS[i], zorder=2)
            self.robot_outlines.append(outline)
            marker = self.ax.scatter(x=[], y=[], marker=self.MARKERS[i],
                        edgecolors='black', linewidths=1, vmin=0, vmax=100,
                        c=[], cmap='Reds_r', zorder=3)
            self.robot_markers.append(marker)

    def init_goldpots(self):
        self.goldpots = self.ax.scatter(x=[], y=[], marker='*', edgecolors='k', c='gold')
        # make the gold glow
        self.goldglow = self.ax.scatter(x=[], y=[], marker='*', c='yellow', alpha=0.3, zorder=1)  

    def init_mines(self):
        self.mines = self.ax.scatter(
            x=[], y=[], marker='X', edgecolors='k', c='red')

    def illustrate_round(self, i):
        def pivot(array):
            return list(zip(*array))

        if not (i+1) % 10:
            print('illustrating step', i+1)

        # figure
        title = str(i+1)
        self.ax.set_title(title, fontsize=20)

        # goldpots
        sizes = []
        # make gold pulse, speed increases as the gold gets older 
        for amount in self.goldamount[i]:
            # faster pulse the older/larger the pot
            pulse_speed = 0.5 + (amount / 200.0) * 0.5
            pulse = 1.0 + 0.4 * np.sin(i * pulse_speed)
            sizes.append(amount * pulse)

        self.goldpots.set_offsets(self.goldpos[i] if self.goldpos[i] else np.empty((0, 2)))
        self.goldpots.set_sizes(sizes if sizes else [])
        self.goldglow.set_offsets(self.goldpos[i] if self.goldpos[i] else np.empty((0, 2)))
        self.goldglow.set_sizes([s * 3 for s in sizes] if sizes else [])

        # robots
        for j, (outline, marker) in enumerate(zip(self.robot_outlines, self.robot_markers)):
            pos = [self.robotspos[i][j]]
            size = self.robotsmoney[i][j]
            outline.set_offsets(pos)
            outline.set_sizes([size * 1.6]) # larger, so that the colored ring peeks out at the edges
            marker.set_offsets(pos)
            marker.set_sizes([size])
            marker.set_array(np.array([self.robotshealth[i][j]]))
            
        # mines
        self.mines.set_offsets(self.minepos[i])

        # trails
        lo = [0, i-5][i-5 >= 0]
        offsets = pivot(self.robotspos[lo:i+1])
        for trail, offset in zip(self.trails, offsets):
            x, y = pivot(list(offset))
            trail.set_data(list(x), list(y))
