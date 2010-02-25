# -*- coding: utf-8 -*-

"""
This is an implementation of the Glicko rating algorithm developed by
Prof. Mark E. Glickman. It is an improvement of the Élő Rating system.
The rating system, as well as this implementation is under public domain
as far as this is possible, if it is not possible, you are free to copy,
distribute and close this code. This program calculates rating changes
for single events as well as RD change over time. It implements the algorithm
as described at:
http://math.bu.edu/people/mg/glicko/
Please use it if you want to understand the implementation.

This application is for a case where there is no discrete rating period.
The RD should be refreshed every once in a while to make sure that the
increase in time is correct. Uncertainty_gain and period_lengths are
really one constant, to keep close to Glickman however, I decided to keep
them seperated. The startvalues should be 1500 and an RD of 350.

NOTE:
    o _Player_ is a dictionary including: "rating" and "RD", "last_time" and
        "new_time" (if it doesn't exist, the current time is taken ...).
    o The time entries can be datetime.datetime OR epoch. Mixed datetimes
        break this version.

CONSTANTS:
    o uncertainty_gain = Faktor that determines how RD increases over one
        rating period. See period_lengths for that. Default is
        so that it takes about 2 years from 80 -> 350.
    o period_length = Lenght of a rating period. The amount of games
        within one should be relatively big. In seconds.
    o minimum_RD and maximum_RD are boundries for the RD. Glickman suggests
        350 as maximu_m. To make sure that a user will have visible rating
        change, and as strengths is never 100% stable, you can introduce
        minimum_RD. Glickman suggests 30 here, and I have to agree.
"""

import math as _m
import time, datetime

# 2 years from 80->350
uncertainty_gain = _m.sqrt((350**2-30**2)/(365.25*2*24*60*60))
_c2 = uncertainty_gain**2
minimum_RD = 30
maximum_RD = 350


def refresh_RD(player):
    """
    player dict -> player dict (with RD changed)
      If no new_time is included, current time is assumed and added too.
      See general help for player dictionary.
    """
    if not player.has_key('new_time'):
        if type(player['new_time'] is datetime):
            player['new_time'] = datetime.datetime.now()
        else:
            player['new_time'] = int(time.time())


    if not player['last_time']:
        player['RD'] = maximum_RD
        return player

    if type(player['new_time'] is datetime):
        dT = (time.mktime(player['new_time'].utctimetuple()) - time.mktime(player['last_time'].utctimetuple()))
    else:
        dT = (player['new_time'] - player['last_time'])

        

    player['RD'] = min(max(_m.sqrt(player['RD']**2+dT*_c2), minimum_RD), maximum_RD)
    return player
    

def match(player1, player2, score):
    """
    player1, player2, score -> player1, player2
      Calculate all changes for a match between player1, player2 with score
      (for player1). Also see refresh_RD which is called for both players.
    """

    player1 = refresh_RD(player1)
    player2 = refresh_RD(player2)
    
    q = _m.log(10)/400
    
    # Note that the players are "mixed".
    player1['g'] = 1/(_m.sqrt(1+3*q**2*player2['RD']**2/_m.pi**2))
    player2['g'] = 1/(_m.sqrt(1+3*q**2*player1['RD']**2/_m.pi**2))
    
    player1['E'] = 1.0/(1.0+10**((-player1['g']*(player1['rating']-player2['rating'])/400)))
    player2['E'] = 1.0/(1.0+10**((-player2['g']*(player2['rating']-player1['rating'])/400)))
    
    player1['1/d^2'] = (q**2*player1['g']**2*player1['E']*(1-player1['E']))
    player2['1/d^2'] = (q**2*player2['g']**2*player2['E']*(1-player2['E']))
    
    player1['rating'] = player1['rating'] + q/(1.0/player1['RD']**2+player1['1/d^2']) * player1['g'] * (score-player1['E'])
    player2['rating'] = player2['rating'] + q/(1.0/player2['RD']**2+player2['1/d^2']) * player2['g'] * ((1-score)-player2['E'])
    
    player1['RD'] = _m.sqrt(1.0/(1.0/player1['RD']**2+player1['1/d^2']))
    player2['RD'] = _m.sqrt(1.0/(1.0/player2['RD']**2+player2['1/d^2']))
    
    return player1, player2


def calibrate_RD_change(old_RD=30, new_RD=350, time=None):
    """
    Calculate and set the uncertainty_gain variable for the set rating
    period, if the RD should increase from old_RD to new_RD in time.
    Note that the two variables really are one ...
    """
    uncertainty_gain = _m.sqrt((new_RD**2-old_RD**2)/(time))
    _c2 = uncertainty_gain**2
    return uncertainty_gain
