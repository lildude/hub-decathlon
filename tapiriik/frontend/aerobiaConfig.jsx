import React from 'react'
import ReactDOM from 'react-dom'

import RuleList from './components/ruleList'

const urlGears = userid =>
    `http://aerobia.ru/users/${userid}/equipments`

class AerobiaConfig extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            requestFailed: false
        }
    }

    componentDidMount() {
        fetch("https://cors-anywhere.herokuapp.com/" + urlGears(this.props.aerobiaId))
            .then(response => {
                if (!response.ok) {
                    throw Error("Network request failed")
                }

                return response
            })
            .then(d => d.json())
            .then(d => {
                this.setState({
                    githubData: d
                })
            }, () => {
                this.setState({
                    requestFailed: true
                })
            })
    }

    render() {
        const { sportTypes } = this.props
        return (
            <div className="fancyTable activitiesTable">
                <p>Настройка инвентаря по умолчанию</p>
                <RuleList 
                    data={[{ key: "1" }, { key: "2" }, { key: "3" }]} 
                    sportTypes={sportTypes}
                />
            </div>
        );
    }
}

ReactDOM.render(
    React.createElement(AerobiaConfig, window.props),
    window.react_mount,
)