import React from 'react'
import ReactDOM from 'react-dom'

import RuleList from './components/ruleList'

const urlGears = (userid, token) =>
    `http://aerobia.ru/users/${userid}/equipments?authentication_token=${token}`

class AerobiaConfig extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            gears: [],
            requestFailed: false,
            gearRules: props.config.gearRules
        }
    }

    componentDidMount() {
        fetch("https://cors-anywhere.herokuapp.com/" + urlGears(this.props.aerobiaId, this.props.userToken))
            .then(response => {
                if (!response.ok) {
                    throw Error("Network request failed");
                }
                return response.text();
            })
            .then(d => {
                var parser = new DOMParser();
                var page = parser.parseFromString(d, "text/html");
                var gears = [];
                var itemNodes = page.getElementsByClassName("item");
                if (!itemNodes.length) {
                    return gears;
                }
                itemNodes = Array.prototype.slice.call(itemNodes);
                itemNodes.forEach(n => {
                    var itemData = n.getElementsByTagName("p")[0];
                    itemData = itemData.getElementsByTagName("a")[0];
                    var gearUrl = itemData.getAttribute("href").split("/");
                    gears.push({
                        id: gearUrl[gearUrl.length - 1],
                        name: itemData.innerText
                    });
                });
                return gears;
            })
            .then(d => {
                this.setState({
                    gears: d
                })
            }, () => {
                this.setState({
                    requestFailed: true
                })
            })
    }

    render() {
        const { sportTypes } = this.props;
        if (this.state.gears.length == 0) return <p>Loading gear...</p>

        return (
            <div className="fancyTable activitiesTable">
                <p>Default gear rules:</p>
                <RuleList 
                    data={this.state.gearRules} 
                    sportTypes={sportTypes}
                    gears={this.state.gears}
                />
            </div>
        );
    }
}

ReactDOM.render(
    React.createElement(AerobiaConfig, window.props),
    window.react_mount,
)