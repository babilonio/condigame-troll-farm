#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

using namespace std;

/**
 * Auto-generated code below aims at helping you parse
 * the standard input according to the problem statement.
 **/

int main()
{
    int width;
    int height;
    cin >> width >> height; cin.ignore();
    for (int i = 0; i < height; i++) {
        string line;
        getline(cin, line);
    }

    // game loop
    while (1) {
        for (int i = 0; i < 2; i++) {
            int plum;
            int lemon;
            int apple;
            int banana;
            int iron;
            int wood;
            cin >> plum >> lemon >> apple >> banana >> iron >> wood; cin.ignore();
        }
        int trees_count;
        cin >> trees_count; cin.ignore();
        for (int i = 0; i < trees_count; i++) {
            string type;
            int x;
            int y;
            int size;
            int health;
            int fruits;
            int cooldown;
            cin >> type >> x >> y >> size >> health >> fruits >> cooldown; cin.ignore();
        }
        int trolls_count;
        cin >> trolls_count; cin.ignore();
        for (int i = 0; i < trolls_count; i++) {
            int id;
            int player;
            int x;
            int y;
            int movement_speed;
            int carry_capacity;
            int harvest_power;
            int chop_power;
            int carry_plum;
            int carry_lemon;
            int carry_apple;
            int carry_banana;
            int carry_iron;
            int carry_wood;
            cin >> id >> player >> x >> y >> movement_speed >> carry_capacity >> harvest_power >> chop_power >> carry_plum >> carry_lemon >> carry_apple >> carry_banana >> carry_iron >> carry_wood; cin.ignore();
        }

        // Write an action using cout. DON'T FORGET THE "<< endl"
        // To debug: cerr << "Debug messages..." << endl;


        // valid actions:
        // MOVE <id> <x> <y>
        // HARVEST <id> - when you are on the same cell as a tree
        // DROP <id> - when you are next to your shack and carry items
        cout << "MOVE 0 7 7" << endl;
    }
}